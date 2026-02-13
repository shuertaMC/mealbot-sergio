import json
import logging

from flask import request

from mealbot.db import query_all
from mealbot.log import (
    log_and_write,
    log_and_write_err,
    log_and_write_status_bad_request,
    log_and_write_status_internal_server_error,
)
from mealbot.org import get_cross_match_trait
from mealbot.utils import get_query_param

logger = logging.getLogger(__name__)


def get_members_from_db(orgname, only_active):
    """Retrieve members from the database with JSONB deserialization.

    Migrated from Go's GetMembersFromDB in members.go.
    Queries the members table and returns a list of member dicts.
    psycopg3 auto-deserializes JSONB columns to Python dicts.

    Note: The Go SQL references 'last_round_with' as the column name.
    The schema.sql defines it as 'pair_counts', but the Go code is the
    source of truth for column names in queries.

    Args:
        orgname: Organization name to filter by.
        only_active: If True, only return active members.

    Returns:
        List of member dicts with keys: organization, email, name,
        metadata (dict[str, str]), last_round_with (dict[str, int]).
    """
    rows = query_all(
        "SELECT organization, name, email, metadata, last_round_with, active "
        "FROM members WHERE organization = $1 ORDER BY name",
        (orgname,),
    )

    members = []
    for row in rows:
        organization, name, email, metadata, last_round_with, active = row

        if only_active and not active:
            continue

        # psycopg3 auto-deserializes JSONB to Python dicts.
        # Ensure we have dicts even if the DB returns None.
        if metadata is None:
            metadata = {}
        if last_round_with is None:
            last_round_with = {}

        members.append({
            "organization": organization,
            "email": email,
            "name": name,
            "metadata": metadata,
            "last_round_with": last_round_with,
        })

    return members


def get_active_members_from_db_as_map(orgname):
    """Return active members as flat dicts with metadata fields merged.

    Migrated from Go's getActiveMembersFromDBAsMap in members.go.
    Each member dict contains 'name', 'email', plus all metadata key/values.

    Args:
        orgname: Organization name to filter by.

    Returns:
        List of MemberResponse-style dicts (flat: name, email, + metadata keys).
    """
    members = get_members_from_db(orgname, True)

    map_members = []
    for member in members:
        map_member = dict(member["metadata"])
        map_member["name"] = member["name"]
        map_member["email"] = member["email"]
        map_members.append(map_member)

    return map_members


def get_active_members_from_db_in_pair_format(orgname):
    """Return active members in a simplified format for pair display.

    Migrated from Go's getActiveMembersFromDBInPairFormat in members.go.
    Returns members with just Name and Email fields, consumed by
    Milestone 4's pairing module.

    Args:
        orgname: Organization name to filter by.

    Returns:
        List of dicts with keys: name, email.
    """
    members = get_members_from_db(orgname, True)

    pair_members = []
    for member in members:
        pair_members.append({
            "name": member["name"],
            "email": member["email"],
        })

    return pair_members


def members_handler():
    """Combined handler for GET and POST /members requests.

    Migrated from Go's MembersHandler in members.go.
    Dispatches to GetMembersHandler for GET, and will dispatch to
    CreateMembersHandler for POST (Task 2).
    """
    if request.method == "GET":
        return get_members_handler()
    elif request.method == "POST":
        # POST /members (CSV upload) will be implemented in Task 2
        return log_and_write_err(
            Exception("POST /members not yet implemented"),
            501,
            "MembersHandler",
        )
    else:
        return log_and_write_err(
            Exception("Only GET and POST requests are allowed at this route"),
            405,
            "MembersHandler",
        )


def get_members_handler():
    """HTTP handler for retrieving members.

    Migrated from Go's GetMembersHandler in members.go.
    Retrieves active members, extracts trait names from metadata,
    fetches the cross-match trait, and returns the combined response.
    """
    function = "GetMembersHandler"

    if request.method != "GET":
        return log_and_write_err(
            Exception("Only GET requests are allowed at this route"),
            405,
            function,
        )

    orgname, err = get_query_param(request, "org")
    if err:
        return log_and_write_status_bad_request(Exception(err), function)

    try:
        members = get_active_members_from_db_as_map(orgname)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    traits = []
    if len(members) > 0:
        for trait in members[0]:
            if trait != "name" and trait != "email":
                traits.append(trait)

    try:
        cross_match_trait = get_cross_match_trait(orgname)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    resp = {
        "members": members,
        "traits": traits,
    }
    if cross_match_trait != "":
        resp["crossMatchTrait"] = cross_match_trait

    try:
        data = json.dumps(resp)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    return log_and_write(data, 200, function)
