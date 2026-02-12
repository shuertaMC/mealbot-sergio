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


class TestGetOrganizationsHandler:
    def test_success(self, client):
        """GET /orgs with valid admin returns org list."""
        with patch("mealbot.org.query_all", return_value=[("org1",), ("org2",)]):
            response = client.get("/orgs?admin=test@example.com")
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert data == {"orgs": ["org1", "org2"]}

    def test_empty_results(self, client):
        """GET /orgs returns empty list when admin has no orgs."""
        with patch("mealbot.org.query_all", return_value=[]):
            response = client.get("/orgs?admin=test@example.com")
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert data == {"orgs": []}

    def test_missing_admin_param(self, client):
        """GET /orgs without admin parameter returns 400."""
        response = client.get("/orgs")
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "request query parameters must contain 'admin'"

    def test_multiple_admin_params(self, client):
        """GET /orgs with multiple admin params returns 400."""
        response = client.get("/orgs?admin=a@test.com&admin=b@test.com")
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "request query parameters must contain 'admin'"

    def test_method_not_allowed_post(self, client):
        """POST /orgs returns 405."""
        response = client.post("/orgs")
        assert response.status_code == 405
        data = json.loads(response.get_data(as_text=True))
        assert "Message" in data

    def test_db_error(self, client):
        """GET /orgs returns 500 on database error."""
        with patch("mealbot.org.query_all", side_effect=Exception("db error")):
            response = client.get("/orgs?admin=test@example.com")
        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "db error"

    def test_response_content_type(self, client):
        """GET /orgs should return application/json content type."""
        with patch("mealbot.org.query_all", return_value=[]):
            response = client.get("/orgs?admin=test@example.com")
        assert response.content_type.startswith("application/json")


class TestCreateOrganizationHandler:
    def test_success(self, client):
        """POST /org with valid data returns 201."""
        with patch("mealbot.org.execute"):
            response = client.post(
                "/org?admin=test@example.com",
                data=json.dumps({"org": "testorg"}),
                content_type="application/json",
            )
        assert response.status_code == 201
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "Successfully created new organization"

    def test_missing_admin_param(self, client):
        """POST /org without admin parameter returns 400."""
        response = client.post(
            "/org",
            data=json.dumps({"org": "testorg"}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "request query parameters must contain 'admin'"

    def test_empty_org_name(self, client):
        """POST /org with empty org name returns 500 (validation error in createOrganization)."""
        response = client.post(
            "/org?admin=test@example.com",
            data=json.dumps({"org": ""}),
            content_type="application/json",
        )
        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "Organization name cannot be an empty string"

    def test_malformed_json(self, client):
        """POST /org with malformed JSON returns 400."""
        response = client.post(
            "/org?admin=test@example.com",
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_method_not_allowed_get(self, client):
        """GET /org returns 405."""
        response = client.get("/org")
        assert response.status_code == 405
        data = json.loads(response.get_data(as_text=True))
        assert "Message" in data

    def test_db_error(self, client):
        """POST /org returns 500 on database error."""
        with patch("mealbot.org.execute", side_effect=Exception("connection failed")):
            response = client.post(
                "/org?admin=test@example.com",
                data=json.dumps({"org": "testorg"}),
                content_type="application/json",
            )
        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "connection failed"

    def test_response_content_type(self, client):
        """POST /org should return application/json content type."""
        with patch("mealbot.org.execute"):
            response = client.post(
                "/org?admin=test@example.com",
                data=json.dumps({"org": "testorg"}),
                content_type="application/json",
            )
        assert response.content_type.startswith("application/json")


class TestCrossMatchTraitHandler:
    def test_success(self, client):
        """POST /crossmatchtrait with valid data returns 201."""
        with patch("mealbot.org.execute"):
            response = client.post(
                "/crossmatchtrait?org=testorg",
                data=json.dumps({"trait": "department"}),
                content_type="application/json",
            )
        assert response.status_code == 201
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "Successfully set the cross match trait"

    def test_missing_org_param(self, client):
        """POST /crossmatchtrait without org parameter returns 400."""
        response = client.post(
            "/crossmatchtrait",
            data=json.dumps({"trait": "department"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_malformed_json(self, client):
        """POST /crossmatchtrait with malformed JSON returns 400."""
        response = client.post(
            "/crossmatchtrait?org=testorg",
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "Request body is malformed"

    def test_method_not_allowed_get(self, client):
        """GET /crossmatchtrait returns 405."""
        response = client.get("/crossmatchtrait")
        assert response.status_code == 405
        data = json.loads(response.get_data(as_text=True))
        assert "Message" in data

    def test_db_error(self, client):
        """POST /crossmatchtrait returns 500 on database error."""
        with patch("mealbot.org.execute", side_effect=Exception("db failure")):
            response = client.post(
                "/crossmatchtrait?org=testorg",
                data=json.dumps({"trait": "department"}),
                content_type="application/json",
            )
        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert data["Message"] == "db failure"

    def test_response_content_type(self, client):
        """POST /crossmatchtrait should return application/json content type."""
        with patch("mealbot.org.execute"):
            response = client.post(
                "/crossmatchtrait?org=testorg",
                data=json.dumps({"trait": "department"}),
                content_type="application/json",
            )
        assert response.content_type.startswith("application/json")


class TestGetCrossMatchTrait:
    def test_returns_trait(self):
        """get_cross_match_trait returns the trait when present."""
        with patch("mealbot.org.query_one", return_value=("department",)):
            from mealbot.org import get_cross_match_trait
            result = get_cross_match_trait("testorg")
        assert result == "department"

    def test_returns_empty_for_null(self):
        """get_cross_match_trait returns empty string when trait is NULL."""
        with patch("mealbot.org.query_one", return_value=(None,)):
            from mealbot.org import get_cross_match_trait
            result = get_cross_match_trait("testorg")
        assert result == ""

    def test_returns_empty_for_no_row(self):
        """get_cross_match_trait returns empty string when no org found."""
        with patch("mealbot.org.query_one", return_value=None):
            from mealbot.org import get_cross_match_trait
            result = get_cross_match_trait("nonexistent")
        assert result == ""


class TestCreateOrganization:
    def test_empty_name_raises(self):
        """create_organization raises ValueError for empty name."""
        from mealbot.org import create_organization
        with pytest.raises(ValueError, match="Organization name cannot be an empty string"):
            create_organization("", "admin@test.com")

    def test_valid_name_calls_execute(self):
        """create_organization calls execute with correct SQL."""
        with patch("mealbot.org.execute") as mock_exec:
            from mealbot.org import create_organization
            create_organization("testorg", "admin@test.com")
        mock_exec.assert_called_once_with(
            "INSERT INTO organizations (name, admin) VALUES ($1, $2)",
            ("testorg", "admin@test.com"),
        )


class TestGetOrganizations:
    def test_returns_list(self):
        """get_organizations returns a list of org names."""
        with patch("mealbot.org.query_all", return_value=[("org1",), ("org2",)]):
            from mealbot.org import get_organizations
            result = get_organizations("admin@test.com")
        assert result == ["org1", "org2"]

    def test_returns_empty_list(self):
        """get_organizations returns empty list when no orgs found."""
        with patch("mealbot.org.query_all", return_value=[]):
            from mealbot.org import get_organizations
            result = get_organizations("admin@test.com")
        assert result == []


class TestStaticFiles:
    def test_privacy_html_accessible(self, client):
        """static/privacy.html should be accessible at /privacy.html."""
        response = client.get("/privacy.html")
        assert response.status_code == 200

    def test_sample_csv_accessible(self, client):
        """static/sample.csv should be accessible at /sample.csv."""
        response = client.get("/sample.csv")
        assert response.status_code == 200
