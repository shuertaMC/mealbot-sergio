"""Tests for request/response logging middleware."""

import logging
import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestRequestLoggingMiddleware:
    """Tests for request/response logging middleware."""

    def test_middleware_logs_request_start(self, caplog):
        """Test that middleware logs incoming request."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.get("/health")

        assert response.status_code == 200

        # Check that request start was logged
        request_logs = [r for r in caplog.records if "Request started" in r.message]
        assert len(request_logs) >= 1

        log_record = request_logs[0]
        assert log_record.method == "GET"
        assert log_record.path == "/health"

    def test_middleware_logs_request_completion(self, caplog):
        """Test that middleware logs response with status code."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.get("/health")

        assert response.status_code == 200

        # Check that request completion was logged
        completion_logs = [r for r in caplog.records if "Request completed" in r.message]
        assert len(completion_logs) >= 1

        log_record = completion_logs[0]
        assert log_record.status_code == 200
        assert hasattr(log_record, "duration_seconds")
        assert log_record.duration_seconds >= 0

    def test_middleware_logs_query_params(self, caplog):
        """Test that middleware logs query parameters."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.get("/health?test=value&foo=bar")

        assert response.status_code == 200

        # Check that query params were logged
        request_logs = [r for r in caplog.records if "Request started" in r.message]
        assert len(request_logs) >= 1

        log_record = request_logs[0]
        assert "test=value" in log_record.query_params
        assert "foo=bar" in log_record.query_params

    def test_middleware_logs_post_request(self, caplog):
        """Test that middleware logs POST requests."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.post("/health", json={"test": "data"})

        # POST to /health returns 405 Method Not Allowed, but that's expected
        assert response.status_code in [200, 405]

        # Check that request was logged with POST method
        request_logs = [r for r in caplog.records if "Request started" in r.message]
        assert len(request_logs) >= 1

        log_record = request_logs[0]
        assert log_record.method == "POST"

    def test_middleware_logs_404_responses(self, caplog):
        """Test that middleware logs 404 responses."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.get("/nonexistent")

        assert response.status_code == 404

        # Check that 404 was logged
        completion_logs = [r for r in caplog.records if "Request completed" in r.message]
        assert len(completion_logs) >= 1

        log_record = completion_logs[0]
        assert log_record.status_code == 404

    def test_middleware_includes_timing_information(self, caplog):
        """Test that middleware includes request duration."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.get("/")

        assert response.status_code == 200

        # Check that timing information is present
        completion_logs = [r for r in caplog.records if "Request completed" in r.message]
        assert len(completion_logs) >= 1

        log_record = completion_logs[0]
        assert hasattr(log_record, "duration_seconds")
        # Duration should be a small positive number (typically < 1 second for these tests)
        assert 0 <= log_record.duration_seconds < 5

    def test_middleware_logs_both_request_and_response(self, caplog):
        """Test that both request start and completion are logged for a single request."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.get("/health")

        assert response.status_code == 200

        # Should have both request start and completion logs
        request_logs = [r for r in caplog.records if "Request started" in r.message]
        completion_logs = [r for r in caplog.records if "Request completed" in r.message]

        assert len(request_logs) >= 1
        assert len(completion_logs) >= 1

    def test_middleware_logs_empty_query_params(self, caplog):
        """Test that middleware handles requests with no query parameters."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.get("/health")

        assert response.status_code == 200

        # Check that query params field is empty
        request_logs = [r for r in caplog.records if "Request started" in r.message]
        assert len(request_logs) >= 1

        log_record = request_logs[0]
        assert log_record.query_params == ""
