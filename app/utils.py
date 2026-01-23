"""HTTP utility functions for consistent error handling and response formatting."""

import logging
from typing import Any, List, Optional

from fastapi import HTTPException, Request


def get_query_param(request: Request, key: str) -> str:
    """
    Extract and validate a single query parameter.

    This function replicates the behavior of utils.go's getQueryParam function:
    - Returns error if the parameter is missing
    - Returns error if the parameter appears more than once
    - Returns the parameter value if exactly one is present

    Args:
        request: FastAPI Request object
        key: The query parameter key to extract

    Returns:
        The query parameter value

    Raises:
        HTTPException: 400 Bad Request if parameter is missing or duplicated
    """
    params = request.query_params.getlist(key)

    if not params or len(params) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Request query parameters must contain {key}"
        )

    return params[0]


def get_query_params(request: Request, keys: List[str]) -> List[str]:
    """
    Extract and validate multiple query parameters.

    This function replicates the behavior of utils.go's getQueryParams function:
    - Returns error if any parameter is missing
    - Returns error if any parameter appears more than once
    - Returns all parameter values in order if all are valid

    Args:
        request: FastAPI Request object
        keys: List of query parameter keys to extract

    Returns:
        List of query parameter values in the same order as keys

    Raises:
        HTTPException: 400 Bad Request if any parameter is missing or duplicated
    """
    values = []

    for key in keys:
        params = request.query_params.getlist(key)

        if not params or len(params) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Request query parameters does not contain {key}"
            )

        values.append(params[0])

    return values


def log_and_raise_error(
    logger: logging.Logger,
    error: Exception,
    status_code: int,
    function_name: str,
    detail: Optional[str] = None
) -> None:
    """
    Log an error and raise an HTTPException.

    This function replicates the behavior of log.go's LogAndWriteErr function:
    - Logs the error with structured fields (status, function)
    - Raises HTTPException with the appropriate status code
    - Includes error message in response body

    Args:
        logger: Logger instance to use for logging
        error: The exception that occurred
        status_code: HTTP status code to return
        function_name: Name of the function where the error occurred
        detail: Optional custom error message (defaults to error message)

    Raises:
        HTTPException: Always raises with the specified status code
    """
    # Log the error with structured fields matching logrus behavior
    logger.error(
        str(error),
        extra={
            "status": status_code,
            "function": function_name,
        }
    )

    # Raise HTTPException with error message in response
    raise HTTPException(
        status_code=status_code,
        detail=detail or str(error)
    )


def log_and_raise_bad_request(
    logger: logging.Logger,
    error: Exception,
    function_name: str,
    detail: Optional[str] = None
) -> None:
    """
    Log an error and raise a 400 Bad Request HTTPException.

    Convenience wrapper around log_and_raise_error for 400 errors.
    Replicates log.go's LogAndWriteStatusBadRequest function.

    Args:
        logger: Logger instance to use for logging
        error: The exception that occurred
        function_name: Name of the function where the error occurred
        detail: Optional custom error message (defaults to error message)

    Raises:
        HTTPException: Always raises with status code 400
    """
    log_and_raise_error(logger, error, 400, function_name, detail)


def log_and_raise_internal_server_error(
    logger: logging.Logger,
    error: Exception,
    function_name: str,
    detail: Optional[str] = None
) -> None:
    """
    Log an error and raise a 500 Internal Server Error HTTPException.

    Convenience wrapper around log_and_raise_error for 500 errors.
    Replicates log.go's LogAndWriteStatusInternalServerError function.

    Args:
        logger: Logger instance to use for logging
        error: The exception that occurred
        function_name: Name of the function where the error occurred
        detail: Optional custom error message (defaults to error message)

    Raises:
        HTTPException: Always raises with status code 500
    """
    log_and_raise_error(logger, error, 500, function_name, detail)


def log_response(
    logger: logging.Logger,
    status_code: int,
    function_name: str,
    message: Optional[str] = None
) -> None:
    """
    Log a successful response.

    This function replicates the behavior of log.go's LogAndWrite function:
    - Logs the status code with DEBUG level
    - Includes function name in structured fields

    Args:
        logger: Logger instance to use for logging
        status_code: HTTP status code being returned
        function_name: Name of the function handling the request
        message: Optional message to include in the log
    """
    logger.debug(
        message or str(status_code),
        extra={
            "function": function_name,
        }
    )
