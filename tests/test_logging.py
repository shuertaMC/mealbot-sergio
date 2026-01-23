"""Tests for logging configuration."""

import json
import logging
from io import StringIO

import pytest

from app.logging_config import setup_logging, get_logger, CustomJsonFormatter


class TestSetupLogging:
    """Tests for setup_logging function."""

    def teardown_method(self):
        """Clean up logging handlers after each test."""
        logger = logging.getLogger()
        logger.handlers.clear()

    def test_setup_logging_default_level(self, capfd):
        """Test that setup_logging configures INFO level by default."""
        setup_logging()

        logger = logging.getLogger("test")
        logger.debug("Debug message")  # Should not appear
        logger.info("Info message")  # Should appear

        captured = capfd.readouterr()
        assert "Debug message" not in captured.out
        assert "Info message" in captured.out

    def test_setup_logging_debug_level(self, capfd):
        """Test that setup_logging can be configured with DEBUG level."""
        setup_logging(log_level="DEBUG")

        logger = logging.getLogger("test")
        logger.debug("Debug message")  # Should appear
        logger.info("Info message")  # Should appear

        captured = capfd.readouterr()
        assert "Debug message" in captured.out
        assert "Info message" in captured.out

    def test_setup_logging_error_level(self, capfd):
        """Test that setup_logging can be configured with ERROR level."""
        setup_logging(log_level="ERROR")

        logger = logging.getLogger("test")
        logger.info("Info message")  # Should not appear
        logger.warning("Warning message")  # Should not appear
        logger.error("Error message")  # Should appear

        captured = capfd.readouterr()
        assert "Info message" not in captured.out
        assert "Warning message" not in captured.out
        assert "Error message" in captured.out

    def test_setup_logging_json_format(self, capfd):
        """Test that setup_logging can use JSON formatting."""
        setup_logging(log_level="INFO", use_json=True)

        logger = logging.getLogger("test")
        logger.info("Test message")

        captured = capfd.readouterr()

        # Parse the JSON output
        try:
            log_line = captured.out.strip()
            log_data = json.loads(log_line)

            # Verify JSON structure
            assert "message" in log_data
            assert log_data["message"] == "Test message"
            assert "logger" in log_data
            assert log_data["logger"] == "logrus"
            assert "level" in log_data
            assert log_data["level"] == "INFO"
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {captured.out}")

    def test_setup_logging_plain_text_format(self, capfd):
        """Test that setup_logging can use plain text formatting."""
        setup_logging(log_level="INFO", use_json=False)

        logger = logging.getLogger("test")
        logger.info("Test message")

        captured = capfd.readouterr()

        # Verify plain text format (not JSON)
        assert "Test message" in captured.out
        assert "INFO" in captured.out
        # Should not be JSON
        assert not captured.out.strip().startswith("{")

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers."""
        # Add a handler manually
        logger = logging.getLogger()
        initial_count = len(logger.handlers)
        handler1 = logging.StreamHandler()
        logger.addHandler(handler1)

        assert len(logger.handlers) == initial_count + 1

        # Setup logging should clear existing handlers
        setup_logging()

        # Should have exactly one handler (the new one), not including pytest handlers
        # Note: pytest may add its own handlers, so we just check that handler1 is not in the list
        assert handler1 not in logger.handlers

    def test_setup_logging_invalid_level_defaults_to_info(self, capfd):
        """Test that invalid log level defaults to INFO."""
        setup_logging(log_level="INVALID")

        logger = logging.getLogger("test")
        logger.debug("Debug message")  # Should not appear
        logger.info("Info message")  # Should appear

        captured = capfd.readouterr()
        assert "Debug message" not in captured.out
        assert "Info message" in captured.out


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_with_name(self):
        """Test getting a logger with a custom name."""
        logger = get_logger("custom_logger")

        assert logger.name == "custom_logger"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_without_name(self):
        """Test getting a logger without specifying a name."""
        logger = get_logger()

        assert logger.name == "app.logging_config"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns the same instance for the same name."""
        logger1 = get_logger("test_logger")
        logger2 = get_logger("test_logger")

        assert logger1 is logger2


class TestCustomJsonFormatter:
    """Tests for CustomJsonFormatter."""

    def test_custom_json_formatter_adds_standard_fields(self):
        """Test that CustomJsonFormatter adds required fields."""
        setup_logging(log_level="INFO", use_json=True)

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = CustomJsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        handler.setFormatter(formatter)

        logger = logging.getLogger("test_formatter")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log a message from a function
        def test_function():
            logger.info("Test message")

        test_function()

        # Parse the JSON output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        # Verify required fields
        assert log_data["logger"] == "logrus"
        assert log_data["level"] == "INFO"
        assert log_data["function"] == "test_function"
        assert log_data["message"] == "Test message"

    def test_custom_json_formatter_with_extra_fields(self):
        """Test that CustomJsonFormatter preserves extra fields."""
        setup_logging(log_level="INFO", use_json=True)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = CustomJsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        handler.setFormatter(formatter)

        logger = logging.getLogger("test_formatter")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log with extra fields (like utils.py does)
        logger.info("Test message", extra={"status": 404, "function": "custom_func"})

        output = stream.getvalue().strip()
        log_data = json.loads(output)

        # Verify extra fields are preserved
        assert log_data["status"] == 404
        assert log_data["function"] == "custom_func"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "logrus"


class TestLoggingIntegration:
    """Integration tests for logging setup."""

    def teardown_method(self):
        """Clean up logging handlers after each test."""
        logger = logging.getLogger()
        logger.handlers.clear()

    def test_logging_with_structured_fields(self, capfd):
        """Test logging with structured fields like the Go implementation."""
        setup_logging(log_level="ERROR", use_json=True)

        logger = logging.getLogger("integration_test")

        # Simulate error logging with structured fields (like utils.py)
        logger.error(
            "Database connection failed",
            extra={
                "status": 500,
                "function": "create_organization",
            }
        )

        captured = capfd.readouterr()
        log_data = json.loads(captured.out.strip())

        assert log_data["message"] == "Database connection failed"
        assert log_data["level"] == "ERROR"
        assert log_data["logger"] == "logrus"
        assert log_data["status"] == 500
        assert log_data["function"] == "create_organization"

    def test_logging_multiple_messages(self, capfd):
        """Test logging multiple messages maintains correct format."""
        setup_logging(log_level="INFO", use_json=True)

        logger = logging.getLogger("test")
        logger.info("First message")
        logger.warning("Second message")
        logger.error("Third message")

        captured = capfd.readouterr()
        lines = captured.out.strip().split("\n")

        assert len(lines) == 3

        for line in lines:
            log_data = json.loads(line)
            assert "message" in log_data
            assert "logger" in log_data
            assert "level" in log_data
