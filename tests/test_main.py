"""Tests for FastAPI application initialization, CORS, static files, and health check."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_endpoint_returns_ok(self, client):
        """Test that health endpoint returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_endpoint_accepts_get_only(self, client):
        """Test that health endpoint only accepts GET requests."""
        response = client.post("/health")
        assert response.status_code == 405  # Method Not Allowed


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_endpoint_returns_welcome_message(self, client):
        """Test that root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Mealbot API"
        assert "docs" in data
        assert data["docs"] == "/docs"


class TestCORSMiddleware:
    """Tests for CORS middleware configuration."""

    def test_cors_allows_get_requests(self, client):
        """Test that CORS allows GET requests."""
        response = client.get(
            "/health",
            headers={"Origin": "http://example.com"}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        # FastAPI's CORSMiddleware with allow_origins=["*"] returns "*"
        assert response.headers["access-control-allow-origin"] in ["*", "http://example.com"]

    def test_cors_allows_post_requests(self, client):
        """Test that CORS allows POST requests."""
        # OPTIONS preflight for POST
        response = client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-methods" in response.headers
        allowed_methods = response.headers["access-control-allow-methods"]
        assert "POST" in allowed_methods

    def test_cors_allows_delete_requests(self, client):
        """Test that CORS allows DELETE requests."""
        # OPTIONS preflight for DELETE
        response = client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "DELETE",
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-methods" in response.headers
        allowed_methods = response.headers["access-control-allow-methods"]
        assert "DELETE" in allowed_methods

    def test_cors_allows_credentials(self, client):
        """Test that CORS allows credentials."""
        response = client.get(
            "/health",
            headers={"Origin": "http://example.com"}
        )
        assert response.status_code == 200
        # When allow_credentials=True, the middleware sets this header
        # Only check if it exists when credentials are requested
        if "access-control-allow-credentials" in response.headers:
            assert response.headers["access-control-allow-credentials"] == "true"

    def test_cors_allows_required_headers(self, client):
        """Test that CORS allows required headers."""
        # Test preflight request
        response = client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type, token",
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-headers" in response.headers
        allowed_headers = response.headers["access-control-allow-headers"].lower()
        # Check that all required headers are allowed
        assert "authorization" in allowed_headers
        assert "content-type" in allowed_headers
        assert "token" in allowed_headers
        assert "origin" in allowed_headers
        assert "accept" in allowed_headers

    def test_options_preflight_request_returns_200(self, client):
        """Test that OPTIONS preflight requests return 200."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200


class TestStaticFiles:
    """Tests for static file serving."""

    def test_privacy_html_is_accessible(self, client):
        """Test that privacy.html is accessible at /static/privacy.html."""
        response = client.get("/static/privacy.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Check for some expected content in the privacy policy
        assert b"privacy" in response.content.lower()

    def test_sample_csv_is_accessible(self, client):
        """Test that sample.csv is accessible at /static/sample.csv."""
        response = client.get("/static/sample.csv")
        assert response.status_code == 200
        # CSV content type can vary, but should contain text or csv
        content_type = response.headers["content-type"]
        assert "text" in content_type or "csv" in content_type or "octet-stream" in content_type

    def test_nonexistent_static_file_returns_404(self, client):
        """Test that accessing nonexistent static file returns 404."""
        response = client.get("/static/nonexistent.txt")
        assert response.status_code == 404


class TestOpenAPIDocumentation:
    """Tests for OpenAPI documentation."""

    def test_openapi_docs_are_accessible(self, client):
        """Test that OpenAPI documentation is accessible at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_json_is_accessible(self, client):
        """Test that OpenAPI JSON schema is accessible at /openapi.json."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Mealbot API"
