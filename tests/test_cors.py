import pytest
from flask import Flask

from mealbot.cors import ACCESS_CONTROL_ALLOW_HEADERS, setup_cors


@pytest.fixture
def app():
    """Create a Flask test app with CORS configured."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    setup_cors(app)

    @app.route("/test", methods=["GET", "POST", "DELETE"])
    def test_endpoint():
        return "ok", 200

    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestCORSHeaders:
    def test_origin_reflected_in_response(self, client):
        """Access-Control-Allow-Origin should reflect the request Origin header."""
        response = client.get(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"

    def test_different_origin_reflected(self, client):
        """Different origins should be reflected back."""
        response = client.get(
            "/test",
            headers={"Origin": "https://other-domain.com"},
        )
        assert response.headers.get("Access-Control-Allow-Origin") == "https://other-domain.com"

    def test_allow_headers_set(self, client):
        """Access-Control-Allow-Headers should match the Go constant."""
        response = client.get(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        assert response.headers.get("Access-Control-Allow-Headers") == ACCESS_CONTROL_ALLOW_HEADERS

    def test_allow_methods_set(self, client):
        """Access-Control-Allow-Methods should be GET, POST, DELETE."""
        response = client.get(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        assert response.headers.get("Access-Control-Allow-Methods") == "GET, POST, DELETE"

    def test_no_origin_header(self, client):
        """When no Origin header is sent, Access-Control-Allow-Origin should be empty string."""
        response = client.get("/test")
        assert response.headers.get("Access-Control-Allow-Origin") == ""


class TestCORSPreflight:
    def test_options_returns_200(self, client):
        """OPTIONS preflight should return 200."""
        response = client.options(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        assert response.status_code == 200

    def test_options_returns_cors_headers(self, client):
        """OPTIONS preflight should include all CORS headers."""
        response = client.options(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
        assert response.headers.get("Access-Control-Allow-Headers") == ACCESS_CONTROL_ALLOW_HEADERS
        assert response.headers.get("Access-Control-Allow-Methods") == "GET, POST, DELETE"

    def test_options_returns_empty_body(self, client):
        """OPTIONS preflight should return empty body (short-circuit, no handler)."""
        response = client.options(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        assert response.data == b""

    def test_options_on_nonexistent_route(self, client):
        """OPTIONS on a non-existent route should still get CORS headers from before_request."""
        response = client.options(
            "/nonexistent",
            headers={"Origin": "https://example.com"},
        )
        # The before_request handler fires for all routes including non-existent ones
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"


class TestCORSWithRegularRequests:
    def test_get_request_has_cors_headers(self, client):
        """Regular GET requests should include CORS headers."""
        response = client.get(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        assert response.status_code == 200
        assert response.data == b"ok"
        assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"

    def test_post_request_has_cors_headers(self, client):
        """Regular POST requests should include CORS headers."""
        response = client.post(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"

    def test_delete_request_has_cors_headers(self, client):
        """Regular DELETE requests should include CORS headers."""
        response = client.delete(
            "/test",
            headers={"Origin": "https://example.com"},
        )
        # Flask may return 405 if DELETE not allowed on route, but let's test with allowed route
        assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
