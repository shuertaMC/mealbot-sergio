"""Tests for HTTP utility functions."""

import logging
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request
from starlette.datastructures import QueryParams

from app.utils import (
    get_query_param,
    get_query_params,
    log_and_raise_error,
    log_and_raise_bad_request,
    log_and_raise_internal_server_error,
    log_response,
)


class TestGetQueryParam:
    """Tests for get_query_param function."""

    def test_get_query_param_success(self):
        """Test extracting a single valid query parameter."""
        # Create a mock request with a single query parameter
        request = Mock(spec=Request)
        request.query_params = QueryParams({"admin": "test@example.com"})

        result = get_query_param(request, "admin")
        assert result == "test@example.com"

    def test_get_query_param_missing(self):
        """Test that missing parameter raises HTTPException 400."""
        request = Mock(spec=Request)
        request.query_params = QueryParams({})

        with pytest.raises(HTTPException) as exc_info:
            get_query_param(request, "admin")

        assert exc_info.value.status_code == 400
        assert "Request query parameters must contain admin" in exc_info.value.detail

    def test_get_query_param_duplicated(self):
        """Test that duplicated parameter raises HTTPException 400."""
        request = Mock(spec=Request)
        # QueryParams with duplicate keys - using list syntax
        request.query_params = QueryParams([("admin", "user1"), ("admin", "user2")])

        with pytest.raises(HTTPException) as exc_info:
            get_query_param(request, "admin")

        assert exc_info.value.status_code == 400
        assert "Request query parameters must contain admin" in exc_info.value.detail

    def test_get_query_param_empty_value(self):
        """Test that empty parameter value is returned successfully."""
        request = Mock(spec=Request)
        request.query_params = QueryParams({"admin": ""})

        result = get_query_param(request, "admin")
        assert result == ""


class TestGetQueryParams:
    """Tests for get_query_params function."""

    def test_get_query_params_success(self):
        """Test extracting multiple valid query parameters."""
        request = Mock(spec=Request)
        request.query_params = QueryParams({
            "admin": "test@example.com",
            "org": "TestOrg",
            "active": "true"
        })

        result = get_query_params(request, ["admin", "org", "active"])
        assert result == ["test@example.com", "TestOrg", "true"]

    def test_get_query_params_single_param(self):
        """Test extracting a single parameter using get_query_params."""
        request = Mock(spec=Request)
        request.query_params = QueryParams({"admin": "test@example.com"})

        result = get_query_params(request, ["admin"])
        assert result == ["test@example.com"]

    def test_get_query_params_missing_first(self):
        """Test that missing first parameter raises HTTPException 400."""
        request = Mock(spec=Request)
        request.query_params = QueryParams({"org": "TestOrg"})

        with pytest.raises(HTTPException) as exc_info:
            get_query_params(request, ["admin", "org"])

        assert exc_info.value.status_code == 400
        assert "Request query parameters does not contain admin" in exc_info.value.detail

    def test_get_query_params_missing_second(self):
        """Test that missing second parameter raises HTTPException 400."""
        request = Mock(spec=Request)
        request.query_params = QueryParams({"admin": "test@example.com"})

        with pytest.raises(HTTPException) as exc_info:
            get_query_params(request, ["admin", "org"])

        assert exc_info.value.status_code == 400
        assert "Request query parameters does not contain org" in exc_info.value.detail

    def test_get_query_params_duplicated(self):
        """Test that duplicated parameter raises HTTPException 400."""
        request = Mock(spec=Request)
        request.query_params = QueryParams([
            ("admin", "user1"),
            ("admin", "user2"),
            ("org", "TestOrg")
        ])

        with pytest.raises(HTTPException) as exc_info:
            get_query_params(request, ["admin", "org"])

        assert exc_info.value.status_code == 400
        assert "Request query parameters does not contain admin" in exc_info.value.detail

    def test_get_query_params_empty_list(self):
        """Test that empty key list returns empty result."""
        request = Mock(spec=Request)
        request.query_params = QueryParams({"admin": "test@example.com"})

        result = get_query_params(request, [])
        assert result == []


class TestLogAndRaiseError:
    """Tests for log_and_raise_error function."""

    def test_log_and_raise_error_with_exception(self, caplog):
        """Test logging and raising HTTPException with custom status code."""
        logger = logging.getLogger("test_logger")
        error = ValueError("Test error message")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(HTTPException) as exc_info:
                log_and_raise_error(logger, error, 404, "test_function")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Test error message"

        # Verify logging occurred
        assert len(caplog.records) == 1
        assert "Test error message" in caplog.text
        assert caplog.records[0].status == 404
        assert caplog.records[0].function == "test_function"

    def test_log_and_raise_error_with_custom_detail(self, caplog):
        """Test logging with custom detail message."""
        logger = logging.getLogger("test_logger")
        error = ValueError("Original error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(HTTPException) as exc_info:
                log_and_raise_error(
                    logger, error, 400, "test_function", detail="Custom error message"
                )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Custom error message"

        # Log should still contain original error
        assert "Original error" in caplog.text

    def test_log_and_raise_bad_request(self, caplog):
        """Test convenience function for 400 errors."""
        logger = logging.getLogger("test_logger")
        error = ValueError("Bad request error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(HTTPException) as exc_info:
                log_and_raise_bad_request(logger, error, "test_function")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Bad request error"
        assert "Bad request error" in caplog.text

    def test_log_and_raise_internal_server_error(self, caplog):
        """Test convenience function for 500 errors."""
        logger = logging.getLogger("test_logger")
        error = RuntimeError("Internal server error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(HTTPException) as exc_info:
                log_and_raise_internal_server_error(logger, error, "test_function")

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"
        assert "Internal server error" in caplog.text


class TestLogResponse:
    """Tests for log_response function."""

    def test_log_response_with_status_code(self, caplog):
        """Test logging a response with status code."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.DEBUG):
            log_response(logger, 200, "test_function")

        assert len(caplog.records) == 1
        assert "200" in caplog.text
        assert caplog.records[0].function == "test_function"

    def test_log_response_with_message(self, caplog):
        """Test logging a response with custom message."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.DEBUG):
            log_response(logger, 201, "test_function", "Resource created")

        assert len(caplog.records) == 1
        assert "Resource created" in caplog.text
        assert caplog.records[0].function == "test_function"

    def test_log_response_debug_level(self, caplog):
        """Test that log_response uses DEBUG level."""
        logger = logging.getLogger("test_logger")

        # Set level to INFO - should not log
        with caplog.at_level(logging.INFO):
            log_response(logger, 200, "test_function")

        assert len(caplog.records) == 0

        # Set level to DEBUG - should log
        with caplog.at_level(logging.DEBUG):
            log_response(logger, 200, "test_function")

        assert len(caplog.records) == 1
