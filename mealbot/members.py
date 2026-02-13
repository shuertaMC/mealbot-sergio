import csv
import io
import json
import logging

from flask import request

from mealbot.db import execute, query_all
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


def is_valid_format_csv(headers):
    """Validate that CSV headers contain a 'name' column (case-insensitive).

    Migrated from Go's isValidFormatCSV in members.go.

    Args:
        headers: List of header strings from the CSV first row.

    Returns:
        True if at least one header is 'name' (case-insensitive).
    """
    for val in headers:
        if val.lower() == "name":
            return True
    return False


def create_members_from_csv(orgname, file_stream):
    """Parse CSV from a file stream and create/reconcile members.

    Migrated from Go's createMembersFromCSV in members.go.
    Design Decision #1: Uses in-memory file stream (more Pythonic) rather
    than writing to disk and reading back, avoiding filesystem side effects.

    Args:
        orgname: Organization name.
        file_stream: File-like object (e.g., from Flask's request.files).

    Returns:
        List of MemberResponse dicts (flat: name, email, + metadata keys).

    Raises:
        ValueError: If CSV format is invalid (missing 'name' column).
        Exception: On database errors.
    """
    # Wrap the file stream in a text wrapper for csv.reader
    text_stream = io.TextIOWrapper(file_stream, encoding="utf-8")
    reader = csv.reader(text_stream)

    members = []
    headers = []

    for row in reader:
        if len(headers) == 0:
            if is_valid_format_csv(row):
                headers = [val.lower() for val in row]
                continue
            else:
                raise ValueError("CSV must have a column titled 'name'")

        name = ""
        email = ""
        metadata = {}
        for i, val in enumerate(row):
            if headers[i] == "name":
                name = val.strip()
            elif headers[i] == "email":
                email = val.strip()
            else:
                metadata[headers[i]] = val

        members.append({
            "organization": orgname,
            "email": email,
            "name": name,
            "metadata": metadata,
            "last_round_with": {},
        })

    # Initialize LastRoundWith maps for all member pairs
    for i in range(len(members)):
        for j in range(len(members)):
            if i == j:
                continue
            members[i]["last_round_with"][members[j]["email"]] = -1

    save_members_in_db(orgname, members)

    # Return flattened member responses
    members_json = []
    for member in members:
        member_json = dict(member["metadata"])
        member_json["name"] = member["name"]
        member_json["email"] = member["email"]
        members_json.append(member_json)

    return members_json


def save_members_in_db(orgname, new_members):
    """Reconcile and persist members from CSV against existing DB members.

    Migrated from Go's saveMembersInDB in members.go (~140 lines).
    Design Decision #2: Direct 1:1 translation of the Go reconciliation
    algorithm to preserve identical behavior, since the LastRoundWith
    data structure correctness is critical for the pairing algorithm.

    The algorithm:
    1. Build maps of new members and existing DB members by email.
    2. Remove existing members not in the new CSV from the working set.
    3. Update name/metadata of existing members that remain.
    4. Add new emails to existing members' LastRoundWith maps.
    5. Insert brand new members with fully initialized LastRoundWith.
    6. Persist all changes via INSERT/UPDATE SQL.
    7. Deactivate members not in the new CSV.

    Args:
        orgname: Organization name.
        new_members: List of member dicts from CSV parsing.

    Raises:
        Exception: On database errors.
    """
    # Build map of new members by email
    new_members_map = {}
    for member in new_members:
        new_members_map[member["email"]] = member

    # Get all existing members (including inactive) from DB
    members_map = {}
    members = get_members_from_db(orgname, False)
    for member in members:
        members_map[member["email"]] = member

    # Remove existing members that are not in new list
    emails_to_remove = []
    for email in members_map:
        if email not in new_members_map:
            emails_to_remove.append(email)
    for email in emails_to_remove:
        del members_map[email]

    # Update fields of existing member (if existing member changes name or metadata)
    for email in list(members_map.keys()):
        if email in new_members_map:
            members_map[email] = {
                "organization": members_map[email]["organization"],
                "email": members_map[email]["email"],
                "last_round_with": members_map[email]["last_round_with"],
                "name": new_members_map[email]["name"],
                "metadata": new_members_map[email]["metadata"],
            }

    # Update pair counts of existing members with new members
    for email in members_map:
        member = members_map[email]
        for new_email in new_members_map:
            # If new email is not an existing member
            if new_email not in members_map:
                member["last_round_with"][new_email] = -1
        members_map[email] = member

    # Save new members
    for email in new_members_map:
        if email not in members_map:
            last_round_with = {}
            for other_email in new_members_map:
                if other_email == email:
                    continue
                last_round_with[other_email] = -1

            members_map[email] = {
                "organization": orgname,
                "name": new_members_map[email]["name"],
                "email": new_members_map[email]["email"],
                "metadata": new_members_map[email]["metadata"],
                "last_round_with": last_round_with,
            }

    # Build set of existing member emails (before reconciliation)
    existing_member_emails = set()
    for member in members:
        existing_member_emails.add(member["email"])

    # Persist members via INSERT or UPDATE
    for member in members_map.values():
        metadata_json = json.dumps(member["metadata"])
        last_round_with_json = json.dumps(member["last_round_with"])

        if member["email"] not in existing_member_emails:
            # Add new member
            execute(
                "INSERT INTO members (organization, email, name, metadata, last_round_with, active) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                (
                    member["organization"],
                    member["email"],
                    member["name"],
                    metadata_json,
                    last_round_with_json,
                    True,
                ),
            )
        else:
            # Update existing member
            execute(
                "UPDATE members SET name = $1, metadata = $2, last_round_with = $3, active = $4 "
                "WHERE organization = $5 AND email = $6",
                (
                    member["name"],
                    metadata_json,
                    last_round_with_json,
                    True,
                    orgname,
                    member["email"],
                ),
            )

    # Deactivate members not in new CSV (don't delete from DB)
    for email in existing_member_emails:
        if email not in members_map:
            execute(
                "UPDATE members SET active = $1 WHERE organization = $2 AND email = $3",
                (False, orgname, email),
            )


def create_members_handler():
    """HTTP handler for creating members via CSV upload.

    Migrated from Go's CreateMembersHandler in members.go.
    Design Decision #1: Parses CSV directly from Flask's in-memory file
    stream rather than writing to disk first (more Pythonic).
    """
    function = "CreateMembersHandler"

    if request.method != "POST":
        return log_and_write_err(
            Exception("Only POST requests are allowed at this route"),
            405,
            function,
        )

    orgname, err = get_query_param(request, "org")
    if err:
        return log_and_write_status_bad_request(Exception(err), function)

    if "members" not in request.files:
        return log_and_write_status_bad_request(
            Exception("missing members file"),
            function,
        )

    form_file = request.files["members"]

    try:
        members = create_members_from_csv(orgname, form_file.stream)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    traits = []
    if len(members) > 0:
        for trait in members[0]:
            if trait != "name" and trait != "email":
                traits.append(trait)

    resp = {
        "members": members,
        "traits": traits,
    }

    try:
        data = json.dumps(resp)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    return log_and_write(data, 201, function)


def members_handler():
    """Combined handler for GET and POST /members requests.

    Migrated from Go's MembersHandler in members.go.
    Dispatches to get_members_handler for GET and create_members_handler for POST.
    """
    if request.method == "GET":
        return get_members_handler()
    elif request.method == "POST":
        return create_members_handler()
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
