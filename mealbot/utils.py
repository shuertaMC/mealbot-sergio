from fastapi import Request


def get_query_param(request: Request, key: str) -> str | None:
    """Extract a single query parameter value.

    Returns the value if exactly one is present, or None if missing or multiple.
    Mirrors Go's getQueryParam behavior.
    """
    values = request.query_params.getlist(key)
    if len(values) != 1:
        return None
    return values[0]


def get_query_params(request: Request, keys: list[str]) -> list[str] | None:
    """Extract multiple query parameters, each with exactly one value.

    Returns list of values if all keys have exactly one value, or None otherwise.
    Mirrors Go's getQueryParams behavior.
    """
    result = []
    for key in keys:
        values = request.query_params.getlist(key)
        if len(values) != 1:
            return None
        result.append(values[0])
    return result
