"""Integration tests for organization API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.organization import Organization
from app.database import get_db_session


# Test data
TEST_ADMIN = "test@example.com"
TEST_ORG_NAME = "TestOrg"
TEST_ORG_NAME_2 = "TestOrg2"
TEST_TRAIT = "engineering"


# Mock authentication for testing
def mock_get_current_user():
    """Mock authentication dependency for tests."""
    return {"sub": "test_user", "email": TEST_ADMIN}


# Override the authentication dependency
app.dependency_overrides[get_db_session] = lambda: None  # Will be overridden per test


@pytest.fixture
async def client(db_session: AsyncSession):
    """Create an async test client with database session override."""
    # Override the database session dependency
    app.dependency_overrides[get_db_session] = lambda: db_session

    # Mock authentication
    from app.middleware.auth import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestGetOrganizations:
    """Tests for GET /orgs endpoint."""

    async def test_get_organizations_empty_list(self, client: AsyncClient):
        """Test getting organizations when none exist."""
        response = await client.get("/orgs", params={"admin": TEST_ADMIN})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "orgs" in data
        assert data["orgs"] == []

    async def test_get_organizations_with_data(self, client: AsyncClient, db_session: AsyncSession):
        """Test getting organizations when they exist."""
        # Create test organizations
        org1 = Organization(name=TEST_ORG_NAME, admin=TEST_ADMIN)
        org2 = Organization(name=TEST_ORG_NAME_2, admin=TEST_ADMIN)
        db_session.add_all([org1, org2])
        await db_session.commit()

        response = await client.get("/orgs", params={"admin": TEST_ADMIN})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "orgs" in data
        assert len(data["orgs"]) == 2
        assert TEST_ORG_NAME in data["orgs"]
        assert TEST_ORG_NAME_2 in data["orgs"]

    async def test_get_organizations_filters_by_admin(self, client: AsyncClient, db_session: AsyncSession):
        """Test that organizations are filtered by admin."""
        # Create organizations for different admins
        org1 = Organization(name=TEST_ORG_NAME, admin=TEST_ADMIN)
        org2 = Organization(name=TEST_ORG_NAME_2, admin="other@example.com")
        db_session.add_all([org1, org2])
        await db_session.commit()

        response = await client.get("/orgs", params={"admin": TEST_ADMIN})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["orgs"]) == 1
        assert data["orgs"][0] == TEST_ORG_NAME

    async def test_get_organizations_missing_admin_param(self, client: AsyncClient):
        """Test error when admin parameter is missing."""
        response = await client.get("/orgs")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_get_organizations_wrong_method(self, client: AsyncClient):
        """Test error when using wrong HTTP method."""
        response = await client.post("/orgs", params={"admin": TEST_ADMIN})

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.asyncio
class TestCreateOrganization:
    """Tests for POST /org endpoint."""

    async def test_create_organization_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successfully creating a new organization."""
        response = await client.post(
            "/org",
            params={"admin": TEST_ADMIN},
            json={"org": TEST_ORG_NAME}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.text == '"Successfully created new organization"'

        # Verify organization was created in database
        stmt = select(Organization).where(Organization.name == TEST_ORG_NAME)
        result = await db_session.execute(stmt)
        org = result.scalar_one_or_none()

        assert org is not None
        assert org.name == TEST_ORG_NAME
        assert org.admin == TEST_ADMIN
        assert org.cross_match_trait is None

    async def test_create_organization_missing_admin_param(self, client: AsyncClient):
        """Test error when admin parameter is missing."""
        response = await client.post("/org", json={"org": TEST_ORG_NAME})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_create_organization_missing_org_field(self, client: AsyncClient):
        """Test error when org field is missing from body."""
        response = await client.post(
            "/org",
            params={"admin": TEST_ADMIN},
            json={"name": TEST_ORG_NAME}  # Wrong field name
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "org" in response.text.lower()

    async def test_create_organization_empty_body(self, client: AsyncClient):
        """Test error when request body is empty."""
        response = await client.post(
            "/org",
            params={"admin": TEST_ADMIN},
            json={}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_create_organization_empty_name(self, client: AsyncClient):
        """Test error when organization name is empty string."""
        response = await client.post(
            "/org",
            params={"admin": TEST_ADMIN},
            json={"org": ""}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Pydantic validation error message may vary
        assert ("empty" in response.text.lower() or "at least 1 character" in response.text.lower())

    async def test_create_organization_duplicate_name(self, client: AsyncClient, db_session: AsyncSession):
        """Test error when creating organization with duplicate name."""
        # Create first organization
        org = Organization(name=TEST_ORG_NAME, admin=TEST_ADMIN)
        db_session.add(org)
        await db_session.commit()

        # Try to create duplicate
        response = await client.post(
            "/org",
            params={"admin": TEST_ADMIN},
            json={"org": TEST_ORG_NAME}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.text.lower()

    async def test_create_organization_wrong_method(self, client: AsyncClient):
        """Test error when using wrong HTTP method."""
        response = await client.get("/org", params={"admin": TEST_ADMIN})

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.asyncio
class TestSetCrossMatchTrait:
    """Tests for POST /crossmatchtrait endpoint."""

    async def test_set_cross_match_trait_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successfully setting cross match trait."""
        # Create organization first
        org = Organization(name=TEST_ORG_NAME, admin=TEST_ADMIN)
        db_session.add(org)
        await db_session.commit()

        response = await client.post(
            "/crossmatchtrait",
            params={"org": TEST_ORG_NAME},
            json={"trait": TEST_TRAIT}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.text == '"Successfully set the cross match trait"'

        # Verify trait was updated in database
        await db_session.refresh(org)
        assert org.cross_match_trait == TEST_TRAIT

    async def test_set_cross_match_trait_update_existing(self, client: AsyncClient, db_session: AsyncSession):
        """Test updating an existing cross match trait."""
        # Create organization with existing trait
        org = Organization(
            name=TEST_ORG_NAME,
            admin=TEST_ADMIN,
            cross_match_trait="old_trait"
        )
        db_session.add(org)
        await db_session.commit()

        # Update trait
        new_trait = "new_trait"
        response = await client.post(
            "/crossmatchtrait",
            params={"org": TEST_ORG_NAME},
            json={"trait": new_trait}
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify trait was updated
        await db_session.refresh(org)
        assert org.cross_match_trait == new_trait

    async def test_set_cross_match_trait_missing_org_param(self, client: AsyncClient):
        """Test error when org parameter is missing."""
        response = await client.post("/crossmatchtrait", json={"trait": TEST_TRAIT})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_set_cross_match_trait_missing_trait_field(self, client: AsyncClient, db_session: AsyncSession):
        """Test error when trait field is missing from body."""
        # Create organization first
        org = Organization(name=TEST_ORG_NAME, admin=TEST_ADMIN)
        db_session.add(org)
        await db_session.commit()

        response = await client.post(
            "/crossmatchtrait",
            params={"org": TEST_ORG_NAME},
            json={"value": TEST_TRAIT}  # Wrong field name
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_set_cross_match_trait_empty_body(self, client: AsyncClient, db_session: AsyncSession):
        """Test error when request body is empty."""
        # Create organization first
        org = Organization(name=TEST_ORG_NAME, admin=TEST_ADMIN)
        db_session.add(org)
        await db_session.commit()

        response = await client.post(
            "/crossmatchtrait",
            params={"org": TEST_ORG_NAME},
            json={}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_set_cross_match_trait_nonexistent_org(self, client: AsyncClient):
        """Test error when organization doesn't exist."""
        response = await client.post(
            "/crossmatchtrait",
            params={"org": "NonexistentOrg"},
            json={"trait": TEST_TRAIT}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.text.lower()

    async def test_set_cross_match_trait_wrong_method(self, client: AsyncClient):
        """Test error when using wrong HTTP method."""
        response = await client.get(
            "/crossmatchtrait",
            params={"org": TEST_ORG_NAME}
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.asyncio
class TestAuthenticationEnforcement:
    """Tests verifying authentication is enforced on all endpoints."""

    async def test_get_orgs_requires_auth(self):
        """Test that GET /orgs requires authentication."""
        # Create client without authentication override
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/orgs", params={"admin": TEST_ADMIN})
            # Should return 401 Unauthorized without valid token
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_org_requires_auth(self):
        """Test that POST /org requires authentication."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/org",
                params={"admin": TEST_ADMIN},
                json={"org": TEST_ORG_NAME}
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_set_trait_requires_auth(self):
        """Test that POST /crossmatchtrait requires authentication."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/crossmatchtrait",
                params={"org": TEST_ORG_NAME},
                json={"trait": TEST_TRAIT}
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
