"""Tests for the Organization SQLAlchemy model."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


@pytest.mark.asyncio
async def test_create_organization(db_session: AsyncSession):
    """Test creating an organization with valid data."""
    # Create a new organization
    org = Organization(name="test-org", admin="admin@example.com")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    # Verify the organization was created
    assert org.name == "test-org"
    assert org.admin == "admin@example.com"
    assert org.cross_match_trait is None


@pytest.mark.asyncio
async def test_create_organization_with_cross_match_trait(db_session: AsyncSession):
    """Test creating an organization with a cross match trait."""
    # Create an organization with cross_match_trait
    org = Organization(
        name="test-org-2", admin="admin@example.com", cross_match_trait="location"
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    # Verify the organization was created with the trait
    assert org.name == "test-org-2"
    assert org.admin == "admin@example.com"
    assert org.cross_match_trait == "location"


@pytest.mark.asyncio
async def test_organization_name_is_primary_key(db_session: AsyncSession):
    """Test that organization name is unique (primary key)."""
    # Create first organization
    org1 = Organization(name="unique-org", admin="admin1@example.com")
    db_session.add(org1)
    await db_session.commit()

    # Try to create another organization with the same name
    org2 = Organization(name="unique-org", admin="admin2@example.com")
    db_session.add(org2)

    # This should raise an IntegrityError due to duplicate primary key
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_organization_admin_cannot_be_null(db_session: AsyncSession):
    """Test that admin field is required (NOT NULL)."""
    # Try to create an organization without admin
    org = Organization(name="test-org-3", admin=None)
    db_session.add(org)

    # This should raise an IntegrityError due to NOT NULL constraint
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_organization_admin_empty_string_violates_check(db_session: AsyncSession):
    """Test that admin field cannot be an empty string (CHECK constraint)."""
    # Try to create an organization with empty admin string
    org = Organization(name="test-org-4", admin="")
    db_session.add(org)

    # This should raise an IntegrityError due to CHECK constraint
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.commit()

    # Verify the error is related to the CHECK constraint
    assert "organizations_admin_check" in str(exc_info.value)

    await db_session.rollback()


@pytest.mark.asyncio
async def test_organization_cross_match_trait_can_be_null(db_session: AsyncSession):
    """Test that cross_match_trait can be NULL."""
    # Create organization without cross_match_trait
    org = Organization(name="test-org-5", admin="admin@example.com")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    # Verify it was created successfully
    assert org.cross_match_trait is None


@pytest.mark.asyncio
async def test_organization_repr(db_session: AsyncSession):
    """Test the string representation of an organization."""
    org = Organization(name="test-org-6", admin="admin@example.com")
    repr_str = repr(org)

    assert "Organization" in repr_str
    assert "test-org-6" in repr_str
    assert "admin@example.com" in repr_str


@pytest.mark.asyncio
async def test_query_organization_by_name(db_session: AsyncSession):
    """Test querying an organization by its name (primary key)."""
    # Create an organization
    org = Organization(name="query-test-org", admin="admin@example.com")
    db_session.add(org)
    await db_session.commit()

    # Query it back by name
    result = await db_session.execute(
        select(Organization).where(Organization.name == "query-test-org")
    )
    retrieved_org = result.scalar_one_or_none()

    # Verify we got the right organization
    assert retrieved_org is not None
    assert retrieved_org.name == "query-test-org"
    assert retrieved_org.admin == "admin@example.com"


@pytest.mark.asyncio
async def test_update_organization_cross_match_trait(db_session: AsyncSession):
    """Test updating the cross_match_trait of an organization."""
    # Create an organization
    org = Organization(name="update-test-org", admin="admin@example.com")
    db_session.add(org)
    await db_session.commit()

    # Update the cross_match_trait
    result = await db_session.execute(
        select(Organization).where(Organization.name == "update-test-org")
    )
    org = result.scalar_one()
    org.cross_match_trait = "department"
    await db_session.commit()
    await db_session.refresh(org)

    # Verify the update
    assert org.cross_match_trait == "department"
