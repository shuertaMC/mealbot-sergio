from flask import request

# Matches Go's AccessControlAllowHeaders constant
ACCESS_CONTROL_ALLOW_HEADERS = "Authorization, Content-Type, Origin, Accept, token"


def setup_cors(app):
    """Configure CORS on a Flask app, matching Go's GetCorsHandler behavior.

    The Go implementation:
    - Reflects the request Origin header as Access-Control-Allow-Origin
    - Sets Access-Control-Allow-Headers to a specific list
    - Sets Access-Control-Allow-Methods to "GET, POST, DELETE"
    - Returns immediately (without calling handler) for OPTIONS requests

    This uses an @app.after_request handler to set CORS headers on every
    response, and a @app.before_request handler to short-circuit OPTIONS
    preflight requests with a 200 response carrying CORS headers.
    """

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            from flask import make_response
            resp = make_response("", 200)
            origin = request.headers.get("Origin", "")
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Headers"] = ACCESS_CONTROL_ALLOW_HEADERS
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE"
            return resp

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = ACCESS_CONTROL_ALLOW_HEADERS
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE"
        return response
