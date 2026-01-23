"""Logging configuration for the application."""

import logging
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that includes standard fields like logrus."""

    def add_fields(self, log_record, record, message_dict):
        """
        Add custom fields to the log record.

        This method mimics logrus behavior by including:
        - timestamp
        - level (logger severity)
        - logger (always "python" to match logrus logger name)
        - function (the function name where logging occurred)
        - message
        """
        super().add_fields(log_record, record, message_dict)

        # Add logger field (matches logrus "logger": "logrus")
        log_record['logger'] = 'logrus'

        # Add level field
        log_record['level'] = record.levelname

        # Add function field if available and not already set by extra fields
        # This allows utils.py to override the function name for more accurate logging
        if 'function' not in log_record and record.funcName:
            log_record['function'] = record.funcName

        # Rename asctime to timestamp for consistency with logrus
        if 'asctime' in log_record:
            log_record['timestamp'] = log_record.pop('asctime')

        # Rename 'message' to match expected format
        if 'message' not in log_record and 'msg' in log_record:
            log_record['message'] = log_record.pop('msg')


def setup_logging(log_level: str = "INFO", use_json: bool = True) -> None:
    """
    Configure logging for the application.

    This function sets up structured logging with either JSON format (for production)
    or plain text format (for development). It matches the logrus behavior from the
    Go implementation by including fields like logger, status, and function.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting (True) or plain text (False)
    """
    # Get the root logger
    logger = logging.getLogger()

    # Clear any existing handlers
    logger.handlers.clear()

    # Set the log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if use_json:
        # Use JSON formatter for structured logging
        # Note: Don't use rename_fields as it causes KeyError when asctime is not in format string
        formatter = CustomJsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        # Use plain text formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: The name of the logger (typically __name__)

    Returns:
        A configured logger instance
    """
    return logging.getLogger(name or __name__)
