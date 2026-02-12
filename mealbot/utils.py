def get_query_param(request, key):
    """Extract a single query parameter value from a Flask request.

    Mirrors Go's getQueryParam: validates that exactly one value exists
    for the given key. Returns (value, None) on success or
    (None, error_message) on failure.

    Args:
        request: Flask request object
        key: Query parameter name

    Returns:
        Tuple of (value, error). On success error is None.
        On failure value is None and error is a string message.
    """
    values = request.args.getlist(key)
    if len(values) == 0 or len(values) > 1:
        return None, f"Request query parameters must contain {key}"
    return values[0], None


def get_query_params(request, keys):
    """Extract multiple query parameter values from a Flask request.

    Mirrors Go's getQueryParams: validates that exactly one value exists
    for each key. Returns (values_list, None) on success or
    ([], error_message) on failure.

    Args:
        request: Flask request object
        keys: List of query parameter names

    Returns:
        Tuple of (values, error). On success error is None.
        On failure values is an empty list and error is a string message.
    """
    values = []
    for key in keys:
        query_values = request.args.getlist(key)
        if len(query_values) == 0 or len(query_values) > 1:
            return [], f"Request query parameters does not contain {key}"
        values.append(query_values[0])
    return values, None
