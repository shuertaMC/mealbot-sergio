import json
import logging

from flask import make_response

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging to approximate Go's logrus output."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def str_to_bytes(message):
    """Convert a string message to JSON bytes matching Go's server.StrToBytes.

    Returns JSON in the format: {"Message": "..."}
    """
    return json.dumps({"Message": message})


def err_to_bytes(err):
    """Convert an error/exception to JSON bytes matching Go's server.ErrToBytes.

    Returns JSON in the format: {"Message": "..."}
    """
    return json.dumps({"Message": str(err)})


def log_and_write_err(err, status, function):
    """Log an error and return a Flask response with the error as JSON.

    Mirrors Go's LogAndWriteErr: logs the error with structured fields,
    sets the HTTP status code, and writes the error as JSON body.
    """
    logger.error(
        "status=%d function=%s error=%s",
        status,
        function,
        str(err),
    )
    response = make_response(err_to_bytes(err), status)
    response.headers["Content-Type"] = "application/json"
    return response


def log_and_write(data, status, function):
    """Log and return a Flask response with the given data.

    Mirrors Go's LogAndWrite: logs the status with structured fields
    and writes the data as the response body.
    """
    logger.debug("function=%s status=%d", function, status)
    if isinstance(data, (dict, list)):
        body = json.dumps(data)
    elif isinstance(data, str):
        body = data
    else:
        body = str(data)
    response = make_response(body, status)
    response.headers["Content-Type"] = "application/json"
    return response


def log_and_write_status_bad_request(err, function):
    """Log and return a 400 Bad Request response.

    Mirrors Go's LogAndWriteStatusBadRequest.
    """
    return log_and_write_err(err, 400, function)


def log_and_write_status_internal_server_error(err, function):
    """Log and return a 500 Internal Server Error response.

    Mirrors Go's LogAndWriteStatusInternalServerError.
    """
    return log_and_write_err(err, 500, function)
