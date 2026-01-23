"""Tests for Organization Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.organization import (
    CrossMatchTraitUpdate,
    OrganizationBase,
    OrganizationCreate,
    OrganizationRead,
)


def test_organization_base_valid():
    """Test OrganizationBase with valid data."""
    org = OrganizationBase(name="test-org", admin="admin@example.com")
    assert org.name == "test-org"
    assert org.admin == "admin@example.com"


def test_organization_base_empty_name():
    """Test OrganizationBase rejects empty name."""
    with pytest.raises(ValidationError) as exc_info:
        OrganizationBase(name="", admin="admin@example.com")

    errors = exc_info.value.errors()
    assert len(errors) > 0
    assert any("name" in str(error["loc"]) for error in errors)


def test_organization_base_empty_admin():
    """Test OrganizationBase rejects empty admin."""
    with pytest.raises(ValidationError) as exc_info:
        OrganizationBase(name="test-org", admin="")

    errors = exc_info.value.errors()
    assert len(errors) > 0
    assert any("admin" in str(error["loc"]) for error in errors)


def test_organization_base_missing_name():
    """Test OrganizationBase requires name field."""
    with pytest.raises(ValidationError) as exc_info:
        OrganizationBase(admin="admin@example.com")

    errors = exc_info.value.errors()
    assert any("name" in str(error["loc"]) for error in errors)


def test_organization_base_missing_admin():
    """Test OrganizationBase requires admin field."""
    with pytest.raises(ValidationError) as exc_info:
        OrganizationBase(name="test-org")

    errors = exc_info.value.errors()
    assert any("admin" in str(error["loc"]) for error in errors)


def test_organization_create_valid():
    """Test OrganizationCreate with valid data."""
    org = OrganizationCreate(name="test-org", admin="admin@example.com")
    assert org.name == "test-org"
    assert org.admin == "admin@example.com"


def test_organization_create_empty_name():
    """Test OrganizationCreate rejects empty name."""
    with pytest.raises(ValidationError) as exc_info:
        OrganizationCreate(name="", admin="admin@example.com")

    errors = exc_info.value.errors()
    assert any("name" in str(error["loc"]) for error in errors)


def test_organization_create_empty_admin():
    """Test OrganizationCreate rejects empty admin."""
    with pytest.raises(ValidationError) as exc_info:
        OrganizationCreate(name="test-org", admin="")

    errors = exc_info.value.errors()
    assert any("admin" in str(error["loc"]) for error in errors)


def test_organization_read_valid():
    """Test OrganizationRead with valid data."""
    org = OrganizationRead(
        name="test-org", admin="admin@example.com", cross_match_trait="location"
    )
    assert org.name == "test-org"
    assert org.admin == "admin@example.com"
    assert org.cross_match_trait == "location"


def test_organization_read_without_cross_match_trait():
    """Test OrganizationRead with null cross_match_trait."""
    org = OrganizationRead(name="test-org", admin="admin@example.com")
    assert org.name == "test-org"
    assert org.admin == "admin@example.com"
    assert org.cross_match_trait is None


def test_organization_read_with_none_cross_match_trait():
    """Test OrganizationRead explicitly setting cross_match_trait to None."""
    org = OrganizationRead(
        name="test-org", admin="admin@example.com", cross_match_trait=None
    )
    assert org.cross_match_trait is None


def test_organization_read_from_orm():
    """Test OrganizationRead can be created from ORM-like object."""
    # Simulate an ORM model with attributes
    class MockOrg:
        name = "test-org"
        admin = "admin@example.com"
        cross_match_trait = "department"

    org = OrganizationRead.model_validate(MockOrg())
    assert org.name == "test-org"
    assert org.admin == "admin@example.com"
    assert org.cross_match_trait == "department"


def test_organization_read_from_dict():
    """Test OrganizationRead can be created from dictionary."""
    data = {"name": "test-org", "admin": "admin@example.com", "cross_match_trait": "team"}
    org = OrganizationRead(**data)
    assert org.name == "test-org"
    assert org.admin == "admin@example.com"
    assert org.cross_match_trait == "team"


def test_cross_match_trait_update_valid():
    """Test CrossMatchTraitUpdate with valid data."""
    update = CrossMatchTraitUpdate(trait="location")
    assert update.trait == "location"


def test_cross_match_trait_update_empty_string():
    """Test CrossMatchTraitUpdate allows empty string."""
    # Based on Go implementation, trait can be set to any string including empty
    update = CrossMatchTraitUpdate(trait="")
    assert update.trait == ""


def test_cross_match_trait_update_missing_trait():
    """Test CrossMatchTraitUpdate requires trait field."""
    with pytest.raises(ValidationError) as exc_info:
        CrossMatchTraitUpdate()

    errors = exc_info.value.errors()
    assert any("trait" in str(error["loc"]) for error in errors)


def test_organization_read_json_serialization():
    """Test OrganizationRead can be serialized to JSON."""
    org = OrganizationRead(
        name="test-org", admin="admin@example.com", cross_match_trait="location"
    )
    json_data = org.model_dump()
    assert json_data["name"] == "test-org"
    assert json_data["admin"] == "admin@example.com"
    assert json_data["cross_match_trait"] == "location"


def test_organization_create_json_serialization():
    """Test OrganizationCreate can be serialized to JSON."""
    org = OrganizationCreate(name="test-org", admin="admin@example.com")
    json_data = org.model_dump()
    assert json_data["name"] == "test-org"
    assert json_data["admin"] == "admin@example.com"
