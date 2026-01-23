"""Pydantic schemas for organization API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional


class OrganizationBase(BaseModel):
    """Base schema with common organization fields."""

    name: str = Field(..., min_length=1, description="Organization name")
    admin: str = Field(..., min_length=1, description="Admin email or identifier")


class OrganizationCreate(BaseModel):
    """Schema for creating a new organization via POST /org."""

    name: str = Field(..., min_length=1, description="Organization name")
    admin: str = Field(..., min_length=1, description="Admin email or identifier")


class OrganizationRead(BaseModel):
    """Schema for reading organization data in API responses."""

    name: str
    admin: str
    cross_match_trait: Optional[str] = None

    class Config:
        """Pydantic config to enable ORM mode."""

        from_attributes = True


class OrganizationCreateBody(BaseModel):
    """Schema for POST /org request body."""

    org: str = Field(..., min_length=1, description="Organization name")


class CrossMatchTraitUpdate(BaseModel):
    """Schema for updating cross match trait via POST /crossmatchtrait."""

    trait: str = Field(..., description="Cross match trait value")
