import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from mealbot.tests.conftest import _create_test_app


# ---------------------------------------------------------------------------
# GET /orgs
# ---------------------------------------------------------------------------

class TestGetOrganizations:
    @pytest.fixture
    def app_with_db(self, authenticated_user, mock_session):
        """App with auth override and mock session."""
        return _create_test_app(
            auth_user=authenticated_user, session_mock=mock_session
        )

    async def test_get_orgs_returns_list(self, mock_session):
        """GET /orgs?admin=<admin> returns {"orgs": [...]} with status 200."""
        # Mock DB result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("org1",), ("org2",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/orgs?admin=testadmin")

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"orgs": ["org1", "org2"]}

    async def test_get_orgs_empty_list(self, mock_session):
        """GET /orgs?admin=<admin> returns empty list when no orgs."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/orgs?admin=nobody")

        assert resp.status_code == 200
        assert resp.json() == {"orgs": []}

    async def test_get_orgs_missing_admin_param(self, mock_session):
        """GET /orgs without admin param returns 400."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/orgs")

        assert resp.status_code == 400
        data = resp.json()
        assert "Message" in data
        assert "admin" in data["Message"].lower()

    async def test_get_orgs_multiple_admin_params(self, mock_session):
        """GET /orgs with multiple admin values returns 400."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/orgs?admin=a&admin=b")

        assert resp.status_code == 400

    async def test_get_orgs_requires_auth(self, mock_session):
        """GET /orgs without auth returns 401."""
        app = _create_test_app(session_mock=mock_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/orgs?admin=test")

        assert resp.status_code == 401

    async def test_get_orgs_db_error(self, mock_session):
        """GET /orgs returns 500 on DB error."""
        mock_session.execute = AsyncMock(side_effect=Exception("DB connection failed"))

        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/orgs?admin=testadmin")

        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /org
# ---------------------------------------------------------------------------

class TestCreateOrganization:
    async def test_create_org_success(self, mock_session):
        """POST /org creates org and returns 201 with success message."""
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/org?admin=testadmin",
                json={"org": "myorg"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data == {"Message": "Successfully created new organization"}

    async def test_create_org_missing_admin(self, mock_session):
        """POST /org without admin returns 400."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/org", json={"org": "myorg"})

        assert resp.status_code == 400

    async def test_create_org_empty_name(self, mock_session):
        """POST /org with empty org name returns 500."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/org?admin=testadmin",
                json={"org": ""},
            )

        assert resp.status_code == 500
        data = resp.json()
        assert "Message" in data
        assert "empty" in data["Message"].lower()

    async def test_create_org_malformed_body(self, mock_session):
        """POST /org with malformed body returns 400."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/org?admin=testadmin",
                content="not json",
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 400

    async def test_create_org_requires_auth(self, mock_session):
        """POST /org without auth returns 401."""
        app = _create_test_app(session_mock=mock_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/org?admin=testadmin",
                json={"org": "myorg"},
            )

        assert resp.status_code == 401

    async def test_create_org_db_error(self, mock_session):
        """POST /org returns 500 on DB error (e.g., duplicate key)."""
        mock_session.execute = AsyncMock(
            side_effect=Exception("duplicate key value violates unique constraint")
        )

        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/org?admin=testadmin",
                json={"org": "existingorg"},
            )

        assert resp.status_code == 500

    async def test_create_org_multiple_admin_params(self, mock_session):
        """POST /org with multiple admin values returns 400."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/org?admin=a&admin=b",
                json={"org": "myorg"},
            )

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /crossmatchtrait
# ---------------------------------------------------------------------------

class TestCrossMatchTrait:
    async def test_set_cross_match_trait_success(self, mock_session):
        """POST /crossmatchtrait sets trait and returns 201."""
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/crossmatchtrait?org=myorg",
                json={"trait": "college"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data == {"Message": "Successfully set the cross match trait"}

    async def test_set_cross_match_trait_missing_org(self, mock_session):
        """POST /crossmatchtrait without org param returns 400."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/crossmatchtrait",
                json={"trait": "college"},
            )

        assert resp.status_code == 400

    async def test_set_cross_match_trait_malformed_body(self, mock_session):
        """POST /crossmatchtrait with malformed body returns 400."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/crossmatchtrait?org=myorg",
                content="not json",
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 400

    async def test_set_cross_match_trait_requires_auth(self, mock_session):
        """POST /crossmatchtrait without auth returns 401."""
        app = _create_test_app(session_mock=mock_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/crossmatchtrait?org=myorg",
                json={"trait": "college"},
            )

        assert resp.status_code == 401

    async def test_set_cross_match_trait_db_error(self, mock_session):
        """POST /crossmatchtrait returns 500 on DB error."""
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))

        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/crossmatchtrait?org=myorg",
                json={"trait": "college"},
            )

        assert resp.status_code == 500

    async def test_set_cross_match_trait_multiple_org_params(self, mock_session):
        """POST /crossmatchtrait with multiple org values returns 400."""
        app = _create_test_app(
            auth_user={"sub": "123"}, session_mock=mock_session
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/crossmatchtrait?org=a&org=b",
                json={"trait": "college"},
            )

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# get_cross_match_trait helper
# ---------------------------------------------------------------------------

class TestGetCrossMatchTraitHelper:
    async def test_returns_trait(self):
        """get_cross_match_trait returns the trait string."""
        from mealbot.org import get_cross_match_trait

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("college",)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_cross_match_trait("myorg", mock_session)
        assert result == "college"

    async def test_returns_empty_for_null(self):
        """get_cross_match_trait returns '' when trait is NULL."""
        from mealbot.org import get_cross_match_trait

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (None,)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_cross_match_trait("myorg", mock_session)
        assert result == ""

    async def test_returns_empty_for_no_row(self):
        """get_cross_match_trait returns '' when org not found."""
        from mealbot.org import get_cross_match_trait

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_cross_match_trait("nonexistent", mock_session)
        assert result == ""
