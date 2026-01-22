"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


@pytest.fixture
def valid_env_vars():
    """Fixture providing a complete set of valid environment variables."""
    return {
        "DATABASE_USER": "test_user",
        "DATABASE_PASSWORD": "test_password",
        "DATABASE_NAME": "test_db",
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": "5432",
        "MAILGUN_API_KEY": "test_api_key",
        "MAILGUN_DOMAIN": "test.mailgun.org",
        "MAILGUN_SMTP_LOGIN": "test@mailgun.org",
        "AUTH0_DOMAIN": "test.auth0.com",
        "AUTH0_AUDIENCE": "https://test.example.com/",
        "PORT": "8080",
        "ENVIRONMENT": "test",
    }


@pytest.fixture
def minimal_env_vars():
    """Fixture providing minimal required environment variables."""
    return {
        "DATABASE_USER": "test_user",
        "DATABASE_NAME": "test_db",
        "MAILGUN_API_KEY": "test_api_key",
        "MAILGUN_DOMAIN": "test.mailgun.org",
        "MAILGUN_SMTP_LOGIN": "test@mailgun.org",
    }


def test_settings_loads_with_valid_env_vars(valid_env_vars):
    """Test that Settings loads successfully with all valid environment variables."""
    with patch.dict(os.environ, valid_env_vars, clear=True):
        settings = Settings()
        assert settings.database_user == "test_user"
        assert settings.database_password == "test_password"
        assert settings.database_name == "test_db"
        assert settings.database_host == "localhost"
        assert settings.database_port == 5432
        assert settings.mailgun_api_key == "test_api_key"
        assert settings.mailgun_domain == "test.mailgun.org"
        assert settings.mailgun_smtp_login == "test@mailgun.org"
        assert settings.auth0_domain == "test.auth0.com"
        assert settings.auth0_audience == "https://test.example.com/"
        assert settings.port == 8080
        assert settings.environment == "test"


def test_settings_applies_defaults(minimal_env_vars):
    """Test that default values are applied when optional fields are not provided."""
    with patch.dict(os.environ, minimal_env_vars, clear=True):
        settings = Settings()
        # Check defaults
        assert settings.database_host == "localhost"
        assert settings.database_port == 5432
        assert settings.database_password == ""
        assert settings.port == 8080
        assert settings.environment == "dev"
        assert settings.auth0_domain == "mealbot.auth0.com"
        assert settings.auth0_audience == "https://mealbot-2.herokuapp.com/"


def test_settings_missing_required_fields():
    """Test that ValidationError is raised when required fields are missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify that multiple required fields are reported as missing
        errors = exc_info.value.errors()
        missing_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}

        # These are the required fields with no defaults
        expected_missing = {
            "database_user",
            "database_name",
            "mailgun_api_key",
            "mailgun_domain",
            "mailgun_smtp_login",
        }
        assert expected_missing.issubset(missing_fields)


def test_settings_database_url_property(valid_env_vars):
    """Test that database_url property constructs the correct URL."""
    with patch.dict(os.environ, valid_env_vars, clear=True):
        settings = Settings()
        expected_url = (
            "postgresql+asyncpg://test_user:test_password"
            "@localhost:5432/test_db"
        )
        assert settings.database_url == expected_url


def test_settings_database_url_without_password(minimal_env_vars):
    """Test that database_url property handles missing password correctly."""
    with patch.dict(os.environ, minimal_env_vars, clear=True):
        settings = Settings()
        expected_url = "postgresql+asyncpg://test_user@localhost:5432/test_db"
        assert settings.database_url == expected_url


def test_settings_auth0_issuer_url_default(valid_env_vars):
    """Test that auth0_issuer_url property defaults to constructed URL from domain."""
    with patch.dict(os.environ, valid_env_vars, clear=True):
        settings = Settings()
        assert settings.auth0_issuer_url == "https://test.auth0.com/"


def test_settings_auth0_issuer_url_explicit(valid_env_vars):
    """Test that auth0_issuer_url property uses explicit issuer when provided."""
    env_with_issuer = {**valid_env_vars, "AUTH0_ISSUER": "https://custom.issuer.com/"}
    with patch.dict(os.environ, env_with_issuer, clear=True):
        settings = Settings()
        assert settings.auth0_issuer_url == "https://custom.issuer.com/"


def test_settings_auth0_jwks_url(valid_env_vars):
    """Test that auth0_jwks_url property constructs the correct JWKS URL."""
    with patch.dict(os.environ, valid_env_vars, clear=True):
        settings = Settings()
        assert settings.auth0_jwks_url == "https://test.auth0.com/.well-known/jwks.json"


def test_settings_port_type_coercion(minimal_env_vars):
    """Test that port is correctly coerced to integer from string."""
    env_with_string_port = {**minimal_env_vars, "PORT": "9000"}
    with patch.dict(os.environ, env_with_string_port, clear=True):
        settings = Settings()
        assert settings.port == 9000
        assert isinstance(settings.port, int)


def test_settings_case_insensitive(minimal_env_vars):
    """Test that environment variable names are case insensitive."""
    lowercase_env = {k.lower(): v for k, v in minimal_env_vars.items()}
    with patch.dict(os.environ, lowercase_env, clear=True):
        settings = Settings()
        assert settings.database_user == "test_user"
        assert settings.database_name == "test_db"


def test_get_settings_singleton():
    """Test that get_settings returns the same instance on multiple calls."""
    # Clear the cache first
    get_settings.cache_clear()

    with patch.dict(
        os.environ,
        {
            "DATABASE_USER": "test_user",
            "DATABASE_NAME": "test_db",
            "MAILGUN_API_KEY": "test_api_key",
            "MAILGUN_DOMAIN": "test.mailgun.org",
            "MAILGUN_SMTP_LOGIN": "test@mailgun.org",
        },
        clear=True,
    ):
        settings1 = get_settings()
        settings2 = get_settings()
        # Due to lru_cache, should return the same instance
        assert settings1 is settings2


def test_settings_auth0_algorithms_default(valid_env_vars):
    """Test that auth0_algorithms has correct default value."""
    with patch.dict(os.environ, valid_env_vars, clear=True):
        settings = Settings()
        assert settings.auth0_algorithms == ["RS256"]
