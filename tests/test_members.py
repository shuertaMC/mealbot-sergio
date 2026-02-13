import io
import json
import os
from unittest.mock import patch

import pytest

from mealbot.app import create_app
from mealbot.members import (
    create_members_from_csv,
    is_valid_format_csv,
    save_members_in_db,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


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
    def test_post_dispatches_to_create_handler(self, client):
        """POST /members dispatches to create_members_handler."""
        # POST without file should return 400 (missing org or file), not 501
        with patch("mealbot.members.execute"):
            with patch("mealbot.members.query_all", return_value=[]):
                response = client.post("/members?org=testorg")
        # Returns 400 for missing file, proving it reached create_members_handler
        assert response.status_code == 400

    def test_get_dispatches_to_get_handler(self, client):
        """GET /members dispatches to get_members_handler."""
        with patch("mealbot.members.query_all", return_value=[]):
            with patch("mealbot.members.get_cross_match_trait", return_value=""):
                response = client.get("/members?org=testorg")
        assert response.status_code == 200


# ============================================================
# Tests for is_valid_format_csv
# ============================================================


class TestIsValidFormatCSV:
    def test_valid_with_name_column(self):
        """is_valid_format_csv returns True when 'name' header exists."""
        assert is_valid_format_csv(["Name", "Email", "College", "Year"]) is True

    def test_valid_case_insensitive(self):
        """is_valid_format_csv is case-insensitive for 'name'."""
        assert is_valid_format_csv(["NAME", "email"]) is True
        assert is_valid_format_csv(["name", "email"]) is True
        assert is_valid_format_csv(["NaMe", "email"]) is True

    def test_invalid_missing_name(self):
        """is_valid_format_csv returns False when 'name' header is missing."""
        assert is_valid_format_csv(["Email", "College", "Year"]) is False

    def test_invalid_empty_headers(self):
        """is_valid_format_csv returns False for empty header list."""
        assert is_valid_format_csv([]) is False

    def test_valid_name_only(self):
        """is_valid_format_csv works with only a 'name' column."""
        assert is_valid_format_csv(["name"]) is True

    def test_invalid_partial_match(self):
        """is_valid_format_csv does not match partial names like 'fullname'."""
        assert is_valid_format_csv(["fullname", "email"]) is False


# ============================================================
# Tests for create_members_from_csv
# ============================================================


class TestCreateMembersFromCSV:
    def _make_csv_stream(self, content):
        """Helper to create a bytes stream from CSV content string."""
        return io.BytesIO(content.encode("utf-8"))

    def test_parse_test_john_fixture(self):
        """create_members_from_csv correctly parses test_john.csv fixture."""
        with open(os.path.join(FIXTURES_DIR, "test_john.csv"), "rb") as f:
            with patch("mealbot.members.save_members_in_db"):
                result = create_members_from_csv("testorg", f)

        assert len(result) == 3
        # Verify first member
        assert result[0]["name"] == "John Yale"
        assert result[0]["email"] == "johnamadeo.daniswara@yale.edu"
        assert result[0]["college"] == "SM"
        assert result[0]["year"] == "2019"
        # Verify second member
        assert result[1]["name"] == "John Gmail"
        assert result[1]["email"] == "johnamadeo.daniswara@gmail.com"
        # Verify third member
        assert result[2]["name"] == "Jadk Gmail"
        assert result[2]["email"] == "jadk157@gmail.com"

    def test_parse_test_john2_fixture(self):
        """create_members_from_csv correctly parses test_john2.csv fixture."""
        with open(os.path.join(FIXTURES_DIR, "test_john2.csv"), "rb") as f:
            with patch("mealbot.members.save_members_in_db"):
                result = create_members_from_csv("testorg", f)

        assert len(result) == 3
        assert result[0]["name"] == "John Yale"
        assert result[1]["name"] == "Jadk Gmail"
        # test_john2.csv has leading space in email " jadk@telkom.net"
        assert result[2]["name"] == "Jadk Telkom"
        assert result[2]["email"] == "jadk@telkom.net"  # trimmed

    def test_parse_test_john3_fixture(self):
        """create_members_from_csv correctly parses test_john3.csv fixture."""
        with open(os.path.join(FIXTURES_DIR, "test_john3.csv"), "rb") as f:
            with patch("mealbot.members.save_members_in_db"):
                result = create_members_from_csv("testorg", f)

        assert len(result) == 4
        assert result[0]["name"] == "John Yale"
        assert result[1]["name"] == "John Gmail"
        assert result[2]["name"] == "Jadk Gmail"
        assert result[3]["name"] == "Jadk Telkom"
        assert result[3]["email"] == "jadk@telkom.net"  # trimmed

    def test_invalid_csv_missing_name_column(self):
        """create_members_from_csv raises ValueError for CSV without 'name' column."""
        stream = self._make_csv_stream("Email,College,Year\ntest@test.com,SM,2019\n")
        with patch("mealbot.members.save_members_in_db"):
            with pytest.raises(ValueError, match="CSV must have a column titled 'name'"):
                create_members_from_csv("testorg", stream)

    def test_whitespace_trimming(self):
        """create_members_from_csv trims whitespace from name and email fields."""
        csv_content = "Name,Email,College\n John Doe , john@test.com ,SM\n"
        stream = self._make_csv_stream(csv_content)
        with patch("mealbot.members.save_members_in_db"):
            result = create_members_from_csv("testorg", stream)
        assert result[0]["name"] == "John Doe"
        assert result[0]["email"] == "john@test.com"

    def test_headers_lowercased(self):
        """create_members_from_csv lowercases all header names."""
        csv_content = "Name,Email,College,Year\nAlice,alice@test.com,SM,2019\n"
        stream = self._make_csv_stream(csv_content)
        with patch("mealbot.members.save_members_in_db"):
            result = create_members_from_csv("testorg", stream)
        assert "college" in result[0]
        assert "year" in result[0]

    def test_flattened_response_format(self):
        """create_members_from_csv returns flat dicts with name, email, and metadata keys."""
        csv_content = "Name,Email,Dept\nAlice,alice@test.com,Engineering\n"
        stream = self._make_csv_stream(csv_content)
        with patch("mealbot.members.save_members_in_db"):
            result = create_members_from_csv("testorg", stream)
        assert len(result) == 1
        member = result[0]
        assert member["name"] == "Alice"
        assert member["email"] == "alice@test.com"
        assert member["dept"] == "Engineering"
        # Should NOT have organization or last_round_with in response
        assert "organization" not in member
        assert "last_round_with" not in member

    def test_calls_save_members_in_db(self):
        """create_members_from_csv calls save_members_in_db with parsed members."""
        csv_content = "Name,Email\nAlice,alice@test.com\nBob,bob@test.com\n"
        stream = self._make_csv_stream(csv_content)
        with patch("mealbot.members.save_members_in_db") as mock_save:
            create_members_from_csv("testorg", stream)

        mock_save.assert_called_once()
        args = mock_save.call_args
        assert args[0][0] == "testorg"
        members = args[0][1]
        assert len(members) == 2
        # Verify LastRoundWith is initialized
        assert members[0]["last_round_with"]["bob@test.com"] == -1
        assert members[1]["last_round_with"]["alice@test.com"] == -1
        # Members should not have themselves in LastRoundWith
        assert "alice@test.com" not in members[0]["last_round_with"]
        assert "bob@test.com" not in members[1]["last_round_with"]

    def test_last_round_with_initialization(self):
        """create_members_from_csv initializes LastRoundWith for all member pairs."""
        csv_content = "Name,Email\nA,a@t.com\nB,b@t.com\nC,c@t.com\n"
        stream = self._make_csv_stream(csv_content)
        with patch("mealbot.members.save_members_in_db") as mock_save:
            create_members_from_csv("testorg", stream)

        members = mock_save.call_args[0][1]
        # Member A should have B and C but not A
        assert members[0]["last_round_with"] == {"b@t.com": -1, "c@t.com": -1}
        # Member B should have A and C but not B
        assert members[1]["last_round_with"] == {"a@t.com": -1, "c@t.com": -1}
        # Member C should have A and B but not C
        assert members[2]["last_round_with"] == {"a@t.com": -1, "b@t.com": -1}


# ============================================================
# Tests for save_members_in_db
# ============================================================


class TestSaveMembersInDB:
    def _make_member(self, email, name="Test", metadata=None, last_round_with=None, org="testorg"):
        return {
            "organization": org,
            "email": email,
            "name": name,
            "metadata": metadata or {},
            "last_round_with": last_round_with or {},
        }

    def test_insert_new_members_no_existing(self):
        """save_members_in_db inserts new members when DB is empty."""
        new_members = [
            self._make_member("alice@test.com", "Alice", {"dept": "eng"},
                              {"bob@test.com": -1}),
            self._make_member("bob@test.com", "Bob", {"dept": "design"},
                              {"alice@test.com": -1}),
        ]

        with patch("mealbot.members.get_members_from_db", return_value=[]):
            with patch("mealbot.members.execute") as mock_exec:
                save_members_in_db("testorg", new_members)

        # Should have 2 INSERT calls (no existing members)
        assert mock_exec.call_count == 2
        for c in mock_exec.call_args_list:
            assert "INSERT INTO members" in c[0][0]

    def test_update_existing_member_name(self):
        """save_members_in_db updates name of existing members."""
        existing_db = [
            self._make_member("alice@test.com", "Old Alice", {"dept": "eng"},
                              {"bob@test.com": 3}),
        ]
        new_members = [
            self._make_member("alice@test.com", "New Alice", {"dept": "eng"},
                              {}),
        ]

        with patch("mealbot.members.get_members_from_db", return_value=existing_db):
            with patch("mealbot.members.execute") as mock_exec:
                save_members_in_db("testorg", new_members)

        # Should be 1 UPDATE call
        assert mock_exec.call_count == 1
        call_args = mock_exec.call_args
        assert "UPDATE members SET" in call_args[0][0]
        # Name should be updated
        assert call_args[0][1][0] == "New Alice"

    def test_update_preserves_last_round_with(self):
        """save_members_in_db preserves existing LastRoundWith history."""
        existing_db = [
            self._make_member("alice@test.com", "Alice", {},
                              {"bob@test.com": 3}),
            self._make_member("bob@test.com", "Bob", {},
                              {"alice@test.com": 3}),
        ]
        new_members = [
            self._make_member("alice@test.com", "Alice", {}, {}),
            self._make_member("bob@test.com", "Bob", {}, {}),
        ]

        with patch("mealbot.members.get_members_from_db", return_value=existing_db):
            with patch("mealbot.members.execute") as mock_exec:
                save_members_in_db("testorg", new_members)

        # Both should be UPDATEs
        assert mock_exec.call_count == 2
        # Check that last_round_with values are preserved
        for c in mock_exec.call_args_list:
            last_round_with_json = c[0][1][2]
            lrw = json.loads(last_round_with_json)
            # Existing value of 3 should be preserved
            assert 3 in lrw.values()

    def test_deactivate_removed_members(self):
        """save_members_in_db deactivates members not in new CSV."""
        existing_db = [
            self._make_member("alice@test.com", "Alice"),
            self._make_member("bob@test.com", "Bob"),
        ]
        new_members = [
            self._make_member("alice@test.com", "Alice"),
        ]

        with patch("mealbot.members.get_members_from_db", return_value=existing_db):
            with patch("mealbot.members.execute") as mock_exec:
                save_members_in_db("testorg", new_members)

        # Should have 1 UPDATE for alice + 1 deactivate for bob
        assert mock_exec.call_count == 2
        deactivate_calls = [c for c in mock_exec.call_args_list
                           if "active = $1" in c[0][0] and c[0][1][0] is False]
        assert len(deactivate_calls) == 1
        assert deactivate_calls[0][0][1][2] == "bob@test.com"

    def test_new_member_gets_last_round_with_for_all(self):
        """save_members_in_db initializes new member's LastRoundWith with all other members."""
        existing_db = [
            self._make_member("alice@test.com", "Alice", {},
                              {"bob@test.com": -1}),
        ]
        new_members = [
            self._make_member("alice@test.com", "Alice", {}, {}),
            self._make_member("bob@test.com", "Bob", {}, {}),  # new member
        ]

        with patch("mealbot.members.get_members_from_db", return_value=existing_db):
            with patch("mealbot.members.execute") as mock_exec:
                save_members_in_db("testorg", new_members)

        # Find the INSERT call (for bob)
        insert_calls = [c for c in mock_exec.call_args_list
                       if "INSERT INTO members" in c[0][0]]
        assert len(insert_calls) == 1
        # Bob's last_round_with should include alice
        lrw = json.loads(insert_calls[0][0][1][4])
        assert lrw == {"alice@test.com": -1}

    def test_existing_member_gets_new_member_in_last_round_with(self):
        """save_members_in_db adds new member emails to existing members' LastRoundWith."""
        existing_db = [
            self._make_member("alice@test.com", "Alice", {},
                              {}),
        ]
        new_members = [
            self._make_member("alice@test.com", "Alice", {}, {}),
            self._make_member("bob@test.com", "Bob", {}, {}),  # brand new
        ]

        with patch("mealbot.members.get_members_from_db", return_value=existing_db):
            with patch("mealbot.members.execute") as mock_exec:
                save_members_in_db("testorg", new_members)

        # Find the UPDATE call (for alice)
        update_calls = [c for c in mock_exec.call_args_list
                       if "UPDATE members SET name" in c[0][0]]
        assert len(update_calls) == 1
        lrw = json.loads(update_calls[0][0][1][2])
        # Alice should now have bob in her LastRoundWith
        assert lrw["bob@test.com"] == -1

    def test_jsonb_serialization(self):
        """save_members_in_db serializes metadata and last_round_with as JSON strings."""
        new_members = [
            self._make_member("alice@test.com", "Alice",
                              {"dept": "eng", "level": "senior"},
                              {"bob@test.com": -1}),
            self._make_member("bob@test.com", "Bob",
                              {"dept": "design"},
                              {"alice@test.com": -1}),
        ]

        with patch("mealbot.members.get_members_from_db", return_value=[]):
            with patch("mealbot.members.execute") as mock_exec:
                save_members_in_db("testorg", new_members)

        # Both calls are INSERTs; find alice's call
        alice_call = None
        for c in mock_exec.call_args_list:
            params = c[0][1]
            if params[1] == "alice@test.com":
                alice_call = c
                break
        assert alice_call is not None
        params = alice_call[0][1]
        # Verify metadata is valid JSON
        metadata = json.loads(params[3])
        assert metadata == {"dept": "eng", "level": "senior"}
        # Verify last_round_with is valid JSON
        lrw = json.loads(params[4])
        assert lrw == {"bob@test.com": -1}

    def test_full_reconciliation_scenario(self):
        """save_members_in_db handles complete reconciliation: add, update, remove."""
        # Existing: alice, bob (active)
        existing_db = [
            self._make_member("alice@test.com", "Alice Old", {"dept": "eng"},
                              {"bob@test.com": 2}),
            self._make_member("bob@test.com", "Bob", {"dept": "design"},
                              {"alice@test.com": 2}),
        ]
        # New CSV: alice (updated name), carol (new) — bob removed
        new_members = [
            self._make_member("alice@test.com", "Alice New", {"dept": "eng"}, {}),
            self._make_member("carol@test.com", "Carol", {"dept": "pm"}, {}),
        ]

        with patch("mealbot.members.get_members_from_db", return_value=existing_db):
            with patch("mealbot.members.execute") as mock_exec:
                save_members_in_db("testorg", new_members)

        # Expected calls:
        # 1. UPDATE alice (name change + carol added to LRW)
        # 2. INSERT carol (new member)
        # 3. Deactivate bob
        assert mock_exec.call_count == 3

        update_calls = [c for c in mock_exec.call_args_list
                       if "UPDATE members SET name" in c[0][0]]
        insert_calls = [c for c in mock_exec.call_args_list
                       if "INSERT INTO members" in c[0][0]]
        deactivate_calls = [c for c in mock_exec.call_args_list
                           if "active = $1" in c[0][0] and c[0][1][0] is False]

        assert len(update_calls) == 1
        assert len(insert_calls) == 1
        assert len(deactivate_calls) == 1

        # Alice should be updated with new name
        alice_update = update_calls[0]
        assert alice_update[0][1][0] == "Alice New"
        alice_lrw = json.loads(alice_update[0][1][2])
        # Alice preserves bob history (2) and adds carol (-1)
        assert alice_lrw["bob@test.com"] == 2
        assert alice_lrw["carol@test.com"] == -1

        # Carol is inserted with alice in her LRW
        carol_insert = insert_calls[0]
        carol_lrw = json.loads(carol_insert[0][1][4])
        assert carol_lrw["alice@test.com"] == -1

        # Bob is deactivated
        assert deactivate_calls[0][0][1][2] == "bob@test.com"


# ============================================================
# Tests for POST /members handler
# ============================================================


class TestCreateMembersHandler:
    def _make_csv_upload(self, client, csv_content, org="testorg", field_name="members", filename="test.csv"):
        """Helper to create a multipart CSV upload request."""
        data = {
            field_name: (io.BytesIO(csv_content.encode("utf-8")), filename),
        }
        return client.post(
            f"/members?org={org}",
            data=data,
            content_type="multipart/form-data",
        )

    def test_success(self, client):
        """POST /members with valid CSV returns 201 with members and traits."""
        csv_content = "Name,Email,College,Year\nAlice,alice@test.com,SM,2019\n"
        with patch("mealbot.members.save_members_in_db"):
            response = self._make_csv_upload(client, csv_content)

        assert response.status_code == 201
        data = json.loads(response.get_data(as_text=True))
        assert "members" in data
        assert "traits" in data
        assert len(data["members"]) == 1
        assert data["members"][0]["name"] == "Alice"
        assert data["members"][0]["email"] == "alice@test.com"
        assert data["members"][0]["college"] == "SM"
        assert data["members"][0]["year"] == "2019"
        # Traits should include metadata keys (college, year) but not name/email
        assert "name" not in data["traits"]
        assert "email" not in data["traits"]

    def test_success_multiple_members(self, client):
        """POST /members with multiple members returns all of them."""
        csv_content = "Name,Email,Dept\nAlice,alice@t.com,Eng\nBob,bob@t.com,Design\n"
        with patch("mealbot.members.save_members_in_db"):
            response = self._make_csv_upload(client, csv_content)

        assert response.status_code == 201
        data = json.loads(response.get_data(as_text=True))
        assert len(data["members"]) == 2

    def test_missing_org_param(self, client):
        """POST /members without org parameter returns 400."""
        data = {
            "members": (io.BytesIO(b"Name,Email\nA,a@t.com\n"), "test.csv"),
        }
        response = client.post("/members", data=data, content_type="multipart/form-data")
        assert response.status_code == 400
        resp_data = json.loads(response.get_data(as_text=True))
        assert "Message" in resp_data

    def test_missing_file(self, client):
        """POST /members without file returns 400."""
        response = client.post("/members?org=testorg")
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert "Message" in data

    def test_invalid_csv_format(self, client):
        """POST /members with CSV missing 'name' column returns 500."""
        csv_content = "Email,College\nalice@test.com,SM\n"
        with patch("mealbot.members.save_members_in_db"):
            response = self._make_csv_upload(client, csv_content)

        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert "name" in data["Message"].lower()

    def test_db_error(self, client):
        """POST /members returns 500 on database error."""
        csv_content = "Name,Email\nAlice,alice@test.com\n"
        with patch("mealbot.members.save_members_in_db", side_effect=Exception("db error")):
            response = self._make_csv_upload(client, csv_content)

        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "db error"

    def test_response_structure(self, client):
        """POST /members returns correct JSON structure with members list and traits."""
        csv_content = "Name,Email,College,Year\nAlice,alice@test.com,SM,2019\nBob,bob@test.com,DM,2020\n"
        with patch("mealbot.members.save_members_in_db"):
            response = self._make_csv_upload(client, csv_content)

        assert response.status_code == 201
        data = json.loads(response.get_data(as_text=True))
        assert isinstance(data["members"], list)
        assert isinstance(data["traits"], list)
        # Each member has flat structure
        for member in data["members"]:
            assert "name" in member
            assert "email" in member

    def test_response_content_type(self, client):
        """POST /members should return application/json content type."""
        csv_content = "Name,Email\nAlice,alice@test.com\n"
        with patch("mealbot.members.save_members_in_db"):
            response = self._make_csv_upload(client, csv_content)
        assert response.content_type.startswith("application/json")

    def test_traits_extracted_from_first_member(self, client):
        """POST /members extracts traits from first member's metadata keys."""
        csv_content = "Name,Email,College,Year\nAlice,alice@test.com,SM,2019\n"
        with patch("mealbot.members.save_members_in_db"):
            response = self._make_csv_upload(client, csv_content)

        data = json.loads(response.get_data(as_text=True))
        traits = data["traits"]
        assert "college" in traits
        assert "year" in traits
        assert "name" not in traits
        assert "email" not in traits

    def test_with_fixture_file(self, client):
        """POST /members with test_john.csv fixture returns 3 members."""
        fixture_path = os.path.join(FIXTURES_DIR, "test_john.csv")
        with open(fixture_path, "rb") as f:
            data = {
                "members": (f, "test_john.csv"),
            }
            with patch("mealbot.members.save_members_in_db"):
                response = client.post(
                    "/members?org=testorg",
                    data=data,
                    content_type="multipart/form-data",
                )

        assert response.status_code == 201
        resp_data = json.loads(response.get_data(as_text=True))
        assert len(resp_data["members"]) == 3
        assert resp_data["members"][0]["name"] == "John Yale"
