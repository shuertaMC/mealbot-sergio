import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from mealbot.auth import require_auth
from mealbot.db import get_session
from mealbot.log import (
    log_and_write,
    log_and_write_bad_request,
    log_and_write_err,
    log_and_write_internal_server_error,
    str_to_dict,
)
from mealbot.models import Organization

logger = logging.getLogger("mealbot")

router = APIRouter()


class CreateOrganizationRequestBody(BaseModel):
    org: str


class SetCrossMatchTraitRequestBody(BaseModel):
    trait: str


@router.get("/orgs")
async def get_organizations_handler(
    request: Request,
    user: dict = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    function = "GetOrganizationsHandler"

    admin = request.query_params.get("admin")
    if admin is None:
        return log_and_write_err(
            "request query parameters must contain 'admin'",
            400,
            function,
        )

    # Check for multiple admin values (Go rejects >1)
    admin_values = request.query_params.getlist("admin")
    if len(admin_values) > 1:
        return log_and_write_err(
            "request query parameters must contain 'admin'",
            400,
            function,
        )

    try:
        result = await session.execute(
            select(Organization.name).where(Organization.admin == admin)
        )
        organizations = [row[0] for row in result.fetchall()]
    except Exception as e:
        return log_and_write_internal_server_error(e, function)

    return log_and_write({"orgs": organizations}, 200, function)


@router.post("/org")
async def create_organization_handler(
    request: Request,
    user: dict = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    function = "CreateOrganizationHandler"

    # Parse JSON body
    try:
        raw_body = await request.json()
    except Exception as e:
        return log_and_write_bad_request(e, function)

    try:
        body = CreateOrganizationRequestBody(**raw_body)
    except Exception as e:
        return log_and_write_bad_request(e, function)

    # Validate admin query parameter
    admin = request.query_params.get("admin")
    if admin is None:
        return log_and_write_err(
            "request query parameters must contain 'admin'",
            400,
            function,
        )

    admin_values = request.query_params.getlist("admin")
    if len(admin_values) > 1:
        return log_and_write_err(
            "request query parameters must contain 'admin'",
            400,
            function,
        )

    logger.info("%s %s", body.org, admin)

    # Validate org name is not empty
    if body.org == "":
        return log_and_write_internal_server_error(
            "Organization name cannot be an empty string", function
        )

    try:
        await session.execute(
            insert(Organization).values(name=body.org, admin=admin)
        )
        await session.commit()
    except Exception as e:
        return log_and_write_internal_server_error(e, function)

    return log_and_write(
        str_to_dict("Successfully created new organization"),
        201,
        function,
    )


@router.post("/crossmatchtrait")
async def cross_match_trait_handler(
    request: Request,
    user: dict = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    function = "CrossMatchTraitHandler"

    # Validate org query parameter
    org = request.query_params.get("org")
    if org is None:
        return log_and_write_bad_request(
            "Request query parameters must contain org", function
        )

    org_values = request.query_params.getlist("org")
    if len(org_values) > 1:
        return log_and_write_bad_request(
            "Request query parameters must contain org", function
        )

    # Parse JSON body
    try:
        raw_body = await request.json()
    except Exception:
        return log_and_write_err("Malformed body.", 400, function)

    try:
        body = SetCrossMatchTraitRequestBody(**raw_body)
    except Exception:
        return log_and_write_err("Request body is malformed", 400, function)

    try:
        await session.execute(
            update(Organization)
            .where(Organization.name == org)
            .values(cross_match_trait=body.trait)
        )
        await session.commit()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"Message": str(e)},
        )

    return log_and_write(
        str_to_dict("Successfully set the cross match trait"),
        201,
        function,
    )


async def get_cross_match_trait(orgname: str, session: AsyncSession) -> str:
    """Retrieve the cross-match trait for an organization.

    Returns the trait string, or empty string if NULL in database.
    This function is exported for use by the pairing algorithm (Milestone 4).
    """
    result = await session.execute(
        select(Organization.cross_match_trait).where(Organization.name == orgname)
    )
    row = result.fetchone()
    if row is None or row[0] is None:
        return ""
    return row[0]
