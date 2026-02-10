from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from fastapi import FastAPI

ALLOWED_HEADERS = "Authorization, Content-Type, Origin, Accept, token"
ALLOWED_METHODS = "GET, POST, DELETE"


class OriginReflectionCORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware that reflects the request Origin header.

    Matches Go cors.go behavior: sets Access-Control-Allow-Origin to the
    request's Origin header value, and short-circuits OPTIONS preflight
    requests.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin", "")

        if request.method == "OPTIONS":
            response = Response(status_code=200)
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
            response.headers["Access-Control-Allow-Methods"] = ALLOWED_METHODS
            return response

        response = await call_next(request)
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
        response.headers["Access-Control-Allow-Methods"] = ALLOWED_METHODS
        return response


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware to match Go cors.go behavior.

    The Go code reflects the request Origin header back and allows
    GET, POST, DELETE methods with Authorization, Content-Type, Origin,
    Accept, and token headers.
    """
    app.add_middleware(OriginReflectionCORSMiddleware)
