from fastapi import Request


def get_query_param(request: Request, key: str) -> tuple[str, str | None]:
    """Extract a single query parameter value.

    Returns (value, None) if exactly one value is present, or
    ("", error_message) if missing or multiple values found.
    Mirrors Go's getQueryParam behavior and error messages.
    """
    values = request.query_params.getlist(key)
    if len(values) == 0 or len(values) > 1:
        return "", f"Request query parameters must contain {key}"
    return values[0], None


def get_query_params(request: Request, keys: list[str]) -> tuple[list[str], str | None]:
    """Extract multiple query parameters, each with exactly one value.

    Returns (values, None) if all keys have exactly one value, or
    ([], error_message) if any key is missing or has multiple values.
    Mirrors Go's getQueryParams behavior and error messages.
    """
    result = []
    for key in keys:
        values = request.query_params.getlist(key)
        if len(values) == 0 or len(values) > 1:
            return [], f"Request query parameters does not contain {key}"
        result.append(values[0])
    return result, None
