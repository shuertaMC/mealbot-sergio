"""Organization management API endpoints."""

from typing import Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.logging_config import get_logger
from app.middleware.auth import get_current_user
from app.models.organization import Organization
from app.schemas.organization import CrossMatchTraitUpdate, OrganizationCreateBody

logger = get_logger(__name__)

router = APIRouter()


def validate_single_query_param(request: Request, param_name: str) -> None:
    """
    Validate that a query parameter appears exactly once.

    Matches Go behavior from utils.go:8-14 where duplicate query parameters
    are rejected with an error.

    Args:
        request: FastAPI request object
        param_name: Name of the query parameter to validate

    Raises:
        HTTPException: 400 if parameter is missing or appears more than once
    """
    values = request.query_params.getlist(param_name)
    if len(values) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request query parameters must contain {param_name}",
        )
    if len(values) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request query parameters must contain exactly one {param_name}",
        )


@router.get("/orgs")
async def get_organizations(
    request: Request,
    admin: str = Query(..., description="Admin email or identifier"),
    db: AsyncSession = Depends(get_db_session),
    user: Dict = Depends(get_current_user),
) -> Dict[str, List[str]]:
    """
    Get all organizations for an admin.

    This endpoint retrieves a list of organization names managed by the specified admin.
    Corresponds to GetOrganizationsHandler in org.go lines 31-69.

    Args:
        request: FastAPI request object
        admin: Admin email or identifier (query parameter)
        db: Database session
        user: Authenticated user from JWT token

    Returns:
        Dict containing a list of organization names: {"orgs": ["org1", "org2"]}

    Raises:
        HTTPException: 400 for duplicate query parameters, 500 for database errors
    """
    function = "get_organizations"

    # Validate exactly one 'admin' parameter (matching org.go:44-45)
    validate_single_query_param(request, "admin")

    logger.info(f"{function}: Fetching organizations for admin={admin}")

    try:
        # Query organizations table for all organizations with matching admin
        # Equivalent to: SELECT name FROM organizations WHERE admin = $1
        stmt = select(Organization.name).where(Organization.admin == admin)
        result = await db.execute(stmt)
        organization_names = result.scalars().all()

        # Convert to list of strings
        orgs = [str(name) for name in organization_names]

        logger.info(f"{function}: Found {len(orgs)} organizations for admin={admin}")
        return {"orgs": orgs}

    except Exception as e:
        logger.error(f"{function}: Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post("/org", status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: Request,
    admin: str = Query(..., description="Admin email or identifier"),
    org_data: OrganizationCreateBody = Body(...),
    db: AsyncSession = Depends(get_db_session),
    user: Dict = Depends(get_current_user),
) -> str:
    """
    Create a new organization.

    This endpoint creates a new organization with the specified name and admin.
    Corresponds to CreateOrganizationHandler in org.go lines 71-124.

    Args:
        request: FastAPI request object
        admin: Admin email or identifier (query parameter)
        org_data: Request body containing {"org": "organization_name"}
        db: Database session
        user: Authenticated user from JWT token

    Returns:
        Success message string

    Raises:
        HTTPException: 400 for validation errors, 500 for database errors
    """
    function = "create_organization"

    # Validate exactly one 'admin' parameter (matching org.go:98-99)
    validate_single_query_param(request, "admin")

    logger.info(f"{function}: Creating organization with admin={admin}")

    # Extract org name from body (Pydantic already validates it's not empty via min_length=1)
    org_name = org_data.org

    try:
        # Create new organization
        # Equivalent to: INSERT INTO organizations (name, admin) VALUES ($1, $2)
        new_org = Organization(name=org_name, admin=admin)
        db.add(new_org)
        await db.commit()

        logger.info(f"{function}: Successfully created organization '{org_name}'")
        return "Successfully created new organization"

    except IntegrityError as e:
        await db.rollback()
        # Handle duplicate organization name (unique constraint violation)
        error_str = str(e).lower()
        if ("unique" in error_str and "organizations.name" in error_str) or \
           ("duplicate" in error_str and "organizations" in error_str):
            logger.error(f"{function}: Organization '{org_name}' already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization '{org_name}' already exists",
            ) from e
        else:
            logger.error(f"{function}: Database integrity error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            ) from e

    except Exception as e:
        await db.rollback()
        logger.error(f"{function}: Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post("/crossmatchtrait", status_code=status.HTTP_201_CREATED)
async def set_cross_match_trait(
    request: Request,
    org: str = Query(..., description="Organization name"),
    body: CrossMatchTraitUpdate = Body(...),
    db: AsyncSession = Depends(get_db_session),
    user: Dict = Depends(get_current_user),
) -> str:
    """
    Set or update the cross match trait for an organization.

    This endpoint updates the cross_match_trait field for the specified organization.
    Corresponds to CrossMatchTraitHandler in org.go lines 126-162.

    Args:
        request: FastAPI request object
        org: Organization name (query parameter)
        body: Request body containing {"trait": "trait_value"}
        db: Database session
        user: Authenticated user from JWT token

    Returns:
        Success message string

    Raises:
        HTTPException: 400 for validation errors, 500 for database errors
    """
    function = "set_cross_match_trait"

    # Validate exactly one 'org' parameter (matching org.go:134-135)
    validate_single_query_param(request, "org")

    logger.info(f"{function}: Setting cross match trait for org={org}")

    try:
        # Find the organization and update cross_match_trait
        # Equivalent to: UPDATE organizations SET cross_match_trait = $1 WHERE name = $2
        stmt = select(Organization).where(Organization.name == org)
        result = await db.execute(stmt)
        organization = result.scalar_one_or_none()

        if not organization:
            logger.error(f"{function}: Organization '{org}' not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization '{org}' not found",
            )

        organization.cross_match_trait = body.trait
        await db.commit()

        logger.info(f"{function}: Successfully set cross match trait for org={org}")
        return "Successfully set the cross match trait"

    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without wrapping
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"{function}: Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
