import json
import logging

from flask import request

from mealbot.db import execute, query_all, query_one
from mealbot.log import (
    err_to_bytes,
    log_and_write,
    log_and_write_err,
    log_and_write_status_bad_request,
    log_and_write_status_internal_server_error,
    str_to_bytes,
)
from mealbot.utils import get_query_param

logger = logging.getLogger(__name__)


def get_organizations_handler():
    """HTTP handler for fetching all the organizations an admin manages.

    Migrated from Go's GetOrganizationsHandler in org.go.
    Go checks: r.Method != "GET" && r.Method != ""
    """
    function = "GetOrganizationsHandler"

    if request.method != "GET":
        return log_and_write_err(
            Exception("Only GET requests are allowed at this route"),
            405,
            function,
        )

    queries = request.args.getlist("admin")
    if not queries or len(queries) > 1:
        return log_and_write_err(
            Exception("request query parameters must contain 'admin'"),
            400,
            function,
        )

    try:
        organizations = get_organizations(queries[0])
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    resp = {"orgs": organizations}
    try:
        data = json.dumps(resp)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    return log_and_write(data, 200, function)


def create_organization_handler():
    """HTTP handler for creating a new organization.

    Migrated from Go's CreateOrganizationHandler in org.go.
    """
    function = "CreateOrganizationHandler"

    if request.method != "POST":
        return log_and_write_err(
            Exception("Only POST requests are allowed at this route"),
            405,
            function,
        )

    try:
        raw_bytes = request.get_data()
    except Exception as e:
        return log_and_write_status_bad_request(e, function)

    try:
        body = json.loads(raw_bytes)
    except Exception as e:
        return log_and_write_status_bad_request(e, function)

    queries = request.args.getlist("admin")
    if not queries or len(queries) > 1:
        return log_and_write_err(
            Exception("request query parameters must contain 'admin'"),
            400,
            function,
        )
    admin = queries[0]

    org_name = body.get("org", "")
    print(org_name, admin)

    try:
        create_organization(org_name, admin)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    return log_and_write(
        str_to_bytes("Successfully created new organization"),
        201,
        function,
    )


def cross_match_trait_handler():
    """HTTP handler for changing or setting a cross match trait for an organization.

    Migrated from Go's CrossMatchTraitHandler in org.go.
    """
    function = "CrossMatchTraitHandler"

    if request.method != "POST":
        return log_and_write_err(
            Exception("Only POST requests are allowed at this route"),
            405,
            function,
        )

    orgname, err = get_query_param(request, "org")
    if err:
        return log_and_write_status_bad_request(Exception(err), function)

    try:
        raw_bytes = request.get_data()
    except Exception as e:
        return log_and_write_err(
            Exception("Malformed body."), 400, function
        )

    try:
        body = json.loads(raw_bytes)
    except Exception as e:
        return log_and_write_err(
            Exception("Request body is malformed"), 400, function
        )

    try:
        set_cross_match_trait(orgname, body.get("trait", ""))
    except Exception as e:
        from flask import make_response
        response = make_response(err_to_bytes(e), 500)
        response.headers["Content-Type"] = "application/json"
        return response

    return log_and_write(
        str_to_bytes("Successfully set the cross match trait"),
        201,
        function,
    )


def get_organizations(admin):
    """Retrieve organization names for a given admin email.

    Migrated from Go's getOrganizations in org.go.
    """
    rows = query_all(
        "SELECT name FROM organizations WHERE admin = $1",
        (admin,),
    )
    return [row[0] for row in rows]


def create_organization(name, admin):
    """Create a new organization.

    Migrated from Go's createOrganization in org.go.
    """
    if not name:
        raise ValueError("Organization name cannot be an empty string")

    execute(
        "INSERT INTO organizations (name, admin) VALUES ($1, $2)",
        (name, admin),
    )


def get_cross_match_trait(orgname):
    """Retrieve the cross-match trait for an organization.

    Handles NULL values from the database (sql.NullString equivalent).
    Migrated from Go's GetCrossMatchTrait in org.go.

    This function is an API export consumed by members handler (Milestone 2)
    and pairing algorithm (Milestone 4).
    """
    row = query_one(
        "SELECT cross_match_trait FROM organizations WHERE name = $1",
        (orgname,),
    )
    if row is None:
        return ""
    return row[0] if row[0] is not None else ""


def set_cross_match_trait(orgname, cross_match_trait):
    """Set the cross-match trait for an organization.

    Migrated from Go's setCrossMatchTrait in org.go.
    """
    execute(
        "UPDATE organizations SET cross_match_trait = $1 WHERE name = $2",
        (cross_match_trait, orgname),
    )
