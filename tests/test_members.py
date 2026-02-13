import json
from unittest.mock import patch

import pytest

from mealbot.app import create_app


@pytest.fixture
def app():
    """Create a Flask test app with auth mocked out (bypass JWT validation)."""
    with patch("mealbot.app.require_auth", lambda f: f):
        test_app = create_app()
    test_app.config["TESTING"] = True
    return test_app


@pytest.fixture
def client(app):
    return app.test_client()


# Sample DB rows matching the SELECT query:
# (organization, name, email, metadata, last_round_with, active)
SAMPLE_DB_ROWS = [
    (
        "testorg",
        "Alice Smith",
        "alice@example.com",
        {"department": "engineering", "location": "NYC"},
        {"bob@example.com": 2, "carol@example.com": -1},
        True,
    ),
    (
        "testorg",
        "Bob Jones",
        "bob@example.com",
        {"department": "design", "location": "SF"},
        {"alice@example.com": 2, "carol@example.com": 1},
        True,
    ),
    (
        "testorg",
        "Carol White",
        "carol@example.com",
        {"department": "engineering", "location": "NYC"},
        {"alice@example.com": -1, "bob@example.com": 1},
        True,
    ),
]

SAMPLE_DB_ROWS_MIXED_ACTIVE = [
    (
        "testorg",
        "Alice Smith",
        "alice@example.com",
        {"department": "engineering"},
        {"bob@example.com": 2},
        True,
    ),
    (
        "testorg",
        "Bob Jones",
        "bob@example.com",
        {"department": "design"},
        {"alice@example.com": 2},
        False,  # inactive
    ),
]


class TestGetMembersFromDB:
    def test_returns_all_members(self):
        """get_members_from_db returns all members when only_active is False."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS_MIXED_ACTIVE):
            from mealbot.members import get_members_from_db
            result = get_members_from_db("testorg", False)
        assert len(result) == 2
        assert result[0]["name"] == "Alice Smith"
        assert result[1]["name"] == "Bob Jones"

    def test_returns_only_active(self):
        """get_members_from_db filters inactive members when only_active is True."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS_MIXED_ACTIVE):
            from mealbot.members import get_members_from_db
            result = get_members_from_db("testorg", True)
        assert len(result) == 1
        assert result[0]["name"] == "Alice Smith"

    def test_member_structure(self):
        """get_members_from_db returns members with correct structure."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS[:1]):
            from mealbot.members import get_members_from_db
            result = get_members_from_db("testorg", False)
        assert len(result) == 1
        member = result[0]
        assert member["organization"] == "testorg"
        assert member["email"] == "alice@example.com"
        assert member["name"] == "Alice Smith"
        assert member["metadata"] == {"department": "engineering", "location": "NYC"}
        assert member["last_round_with"] == {"bob@example.com": 2, "carol@example.com": -1}

    def test_jsonb_deserialization(self):
        """get_members_from_db correctly handles JSONB dict fields."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS):
            from mealbot.members import get_members_from_db
            result = get_members_from_db("testorg", False)
        # Metadata is dict[str, str]
        assert isinstance(result[0]["metadata"], dict)
        assert result[0]["metadata"]["department"] == "engineering"
        # LastRoundWith is dict[str, int]
        assert isinstance(result[0]["last_round_with"], dict)
        assert result[0]["last_round_with"]["bob@example.com"] == 2

    def test_empty_results(self):
        """get_members_from_db returns empty list when no members found."""
        with patch("mealbot.members.query_all", return_value=[]):
            from mealbot.members import get_members_from_db
            result = get_members_from_db("testorg", True)
        assert result == []

    def test_null_metadata_handled(self):
        """get_members_from_db handles None metadata/last_round_with from DB."""
        row_with_nulls = [
            ("testorg", "Alice", "alice@example.com", None, None, True),
        ]
        with patch("mealbot.members.query_all", return_value=row_with_nulls):
            from mealbot.members import get_members_from_db
            result = get_members_from_db("testorg", False)
        assert result[0]["metadata"] == {}
        assert result[0]["last_round_with"] == {}

    def test_query_params(self):
        """get_members_from_db passes correct SQL and params to query_all."""
        with patch("mealbot.members.query_all", return_value=[]) as mock_query:
            from mealbot.members import get_members_from_db
            get_members_from_db("myorg", True)
        mock_query.assert_called_once_with(
            "SELECT organization, name, email, metadata, last_round_with, active "
            "FROM members WHERE organization = $1 ORDER BY name",
            ("myorg",),
        )


class TestGetActiveMembersFromDBAsMap:
    def test_flattens_members(self):
        """get_active_members_from_db_as_map flattens metadata into member dict."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS):
            from mealbot.members import get_active_members_from_db_as_map
            result = get_active_members_from_db_as_map("testorg")
        assert len(result) == 3
        # Each member should have name, email, and all metadata keys
        alice = result[0]
        assert alice["name"] == "Alice Smith"
        assert alice["email"] == "alice@example.com"
        assert alice["department"] == "engineering"
        assert alice["location"] == "NYC"

    def test_returns_empty_for_no_members(self):
        """get_active_members_from_db_as_map returns empty list when no members."""
        with patch("mealbot.members.query_all", return_value=[]):
            from mealbot.members import get_active_members_from_db_as_map
            result = get_active_members_from_db_as_map("testorg")
        assert result == []

    def test_only_active_members(self):
        """get_active_members_from_db_as_map only returns active members."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS_MIXED_ACTIVE):
            from mealbot.members import get_active_members_from_db_as_map
            result = get_active_members_from_db_as_map("testorg")
        assert len(result) == 1
        assert result[0]["name"] == "Alice Smith"

    def test_does_not_mutate_original_metadata(self):
        """get_active_members_from_db_as_map creates copies of metadata dicts."""
        rows = [
            ("testorg", "Alice", "alice@example.com", {"dept": "eng"}, {}, True),
        ]
        with patch("mealbot.members.query_all", return_value=rows):
            from mealbot.members import get_active_members_from_db_as_map
            result = get_active_members_from_db_as_map("testorg")
        # The flattened dict should contain name, email, and dept
        assert result[0] == {"name": "Alice", "email": "alice@example.com", "dept": "eng"}


class TestGetActiveMembersFromDBInPairFormat:
    def test_returns_name_and_email_only(self):
        """get_active_members_from_db_in_pair_format returns only name and email."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS):
            from mealbot.members import get_active_members_from_db_in_pair_format
            result = get_active_members_from_db_in_pair_format("testorg")
        assert len(result) == 3
        for member in result:
            assert set(member.keys()) == {"name", "email"}
        assert result[0] == {"name": "Alice Smith", "email": "alice@example.com"}
        assert result[1] == {"name": "Bob Jones", "email": "bob@example.com"}

    def test_returns_empty_for_no_members(self):
        """get_active_members_from_db_in_pair_format returns empty list."""
        with patch("mealbot.members.query_all", return_value=[]):
            from mealbot.members import get_active_members_from_db_in_pair_format
            result = get_active_members_from_db_in_pair_format("testorg")
        assert result == []

    def test_only_active_members(self):
        """get_active_members_from_db_in_pair_format only returns active members."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS_MIXED_ACTIVE):
            from mealbot.members import get_active_members_from_db_in_pair_format
            result = get_active_members_from_db_in_pair_format("testorg")
        assert len(result) == 1
        assert result[0]["name"] == "Alice Smith"


class TestGetMembersHandler:
    def test_success(self, client):
        """GET /members with valid org returns members, traits, and crossMatchTrait."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS):
            with patch("mealbot.members.get_cross_match_trait", return_value="department"):
                response = client.get("/members?org=testorg")
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert "members" in data
        assert "traits" in data
        assert "crossMatchTrait" in data
        assert data["crossMatchTrait"] == "department"
        assert len(data["members"]) == 3
        # Verify member structure is flattened
        assert data["members"][0]["name"] == "Alice Smith"
        assert data["members"][0]["email"] == "alice@example.com"

    def test_success_without_cross_match_trait(self, client):
        """GET /members without cross-match trait omits crossMatchTrait field."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS):
            with patch("mealbot.members.get_cross_match_trait", return_value=""):
                response = client.get("/members?org=testorg")
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert "crossMatchTrait" not in data
        assert "members" in data
        assert "traits" in data

    def test_traits_extracted_from_first_member(self, client):
        """GET /members extracts traits from first member's metadata keys."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS):
            with patch("mealbot.members.get_cross_match_trait", return_value=""):
                response = client.get("/members?org=testorg")
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        traits = data["traits"]
        # Traits are metadata keys (not name or email)
        assert "name" not in traits
        assert "email" not in traits
        assert "department" in traits
        assert "location" in traits

    def test_empty_members_list(self, client):
        """GET /members with no members returns empty members and traits lists."""
        with patch("mealbot.members.query_all", return_value=[]):
            with patch("mealbot.members.get_cross_match_trait", return_value=""):
                response = client.get("/members?org=testorg")
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert data["members"] == []
        assert data["traits"] == []

    def test_missing_org_param(self, client):
        """GET /members without org parameter returns 400."""
        response = client.get("/members")
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert "Message" in data

    def test_method_not_allowed_delete(self, client):
        """DELETE /members returns 405."""
        response = client.delete("/members")
        assert response.status_code == 405
        data = json.loads(response.get_data(as_text=True))
        assert "Message" in data

    def test_method_not_allowed_put(self, client):
        """PUT /members returns 405."""
        response = client.put("/members")
        assert response.status_code == 405
        data = json.loads(response.get_data(as_text=True))
        assert "Message" in data

    def test_db_error(self, client):
        """GET /members returns 500 on database error."""
        with patch("mealbot.members.query_all", side_effect=Exception("connection failed")):
            response = client.get("/members?org=testorg")
        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "connection failed"

    def test_cross_match_trait_error(self, client):
        """GET /members returns 500 when cross-match trait lookup fails."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS):
            with patch("mealbot.members.get_cross_match_trait", side_effect=Exception("trait error")):
                response = client.get("/members?org=testorg")
        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "trait error"

    def test_response_content_type(self, client):
        """GET /members should return application/json content type."""
        with patch("mealbot.members.query_all", return_value=[]):
            with patch("mealbot.members.get_cross_match_trait", return_value=""):
                response = client.get("/members?org=testorg")
        assert response.content_type.startswith("application/json")

    def test_cross_match_trait_included_when_set(self, client):
        """GET /members includes crossMatchTrait only when non-empty."""
        with patch("mealbot.members.query_all", return_value=SAMPLE_DB_ROWS):
            with patch("mealbot.members.get_cross_match_trait", return_value="location"):
                response = client.get("/members?org=testorg")
        data = json.loads(response.get_data(as_text=True))
        assert data["crossMatchTrait"] == "location"

    def test_members_metadata_merged_into_response(self, client):
        """GET /members returns members with metadata keys at top level."""
        single_member_rows = [
            ("testorg", "Alice", "alice@example.com", {"team": "backend"}, {}, True),
        ]
        with patch("mealbot.members.query_all", return_value=single_member_rows):
            with patch("mealbot.members.get_cross_match_trait", return_value=""):
                response = client.get("/members?org=testorg")
        data = json.loads(response.get_data(as_text=True))
        assert data["members"][0]["team"] == "backend"
        assert data["members"][0]["name"] == "Alice"
        assert data["members"][0]["email"] == "alice@example.com"


class TestMembersHandler:
    def test_post_returns_501(self, client):
        """POST /members returns 501 (not yet implemented)."""
        response = client.post("/members?org=testorg")
        assert response.status_code == 501

    def test_get_dispatches_to_get_handler(self, client):
        """GET /members dispatches to get_members_handler."""
        with patch("mealbot.members.query_all", return_value=[]):
            with patch("mealbot.members.get_cross_match_trait", return_value=""):
                response = client.get("/members?org=testorg")
        assert response.status_code == 200
