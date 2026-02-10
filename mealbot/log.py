import logging
from typing import Any

from fastapi.responses import JSONResponse

logger = logging.getLogger("mealbot")


def str_to_dict(message: str) -> dict[str, str]:
    """Equivalent of Go's server.StrToBytes - returns {"Message": "..."}."""
    return {"Message": message}


def err_to_dict(err: Exception | str) -> dict[str, str]:
    """Equivalent of Go's server.ErrToBytes - returns {"Message": "..."}."""
    message = str(err) if isinstance(err, Exception) else err
    return {"Message": message}


def log_and_write_err(
    err: Exception | str,
    status: int,
    function: str,
) -> JSONResponse:
    logger.error("%s: %s (status=%d)", function, err, status)
    return JSONResponse(content=err_to_dict(err), status_code=status)


def log_and_write(
    content: Any,
    status: int,
    function: str,
) -> JSONResponse:
    logger.debug("%s: status=%d", function, status)
    return JSONResponse(content=content, status_code=status)


def log_and_write_bad_request(err: Exception | str, function: str) -> JSONResponse:
    return log_and_write_err(err, 400, function)


def log_and_write_internal_server_error(err: Exception | str, function: str) -> JSONResponse:
    return log_and_write_err(err, 500, function)
