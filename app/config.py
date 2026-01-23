"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    database_user: str = Field(
        description="PostgreSQL database user"
    )
    database_password: str = Field(
        default="",
        description="PostgreSQL database password"
    )
    database_name: str = Field(
        description="PostgreSQL database name"
    )
    database_host: str = Field(
        default="localhost",
        description="PostgreSQL database host"
    )
    database_port: int = Field(
        default=5432,
        description="PostgreSQL database port"
    )

    # Mailgun Configuration
    mailgun_api_key: str = Field(
        description="Mailgun API key for sending emails"
    )
    mailgun_domain: str = Field(
        description="Mailgun domain for sending emails"
    )
    mailgun_smtp_login: str = Field(
        description="Mailgun SMTP login address"
    )

    # Auth0 Configuration
    auth0_domain: str = Field(
        default="mealbot.auth0.com",
        description="Auth0 domain for JWT validation"
    )
    auth0_audience: str = Field(
        default="https://mealbot-2.herokuapp.com/",
        description="Auth0 audience for JWT validation"
    )
    auth0_issuer: Optional[str] = Field(
        default=None,
        description="Auth0 issuer for JWT validation (defaults to https://{auth0_domain}/)"
    )
    auth0_algorithms: list[str] = Field(
        default=["RS256"],
        description="Allowed JWT signing algorithms"
    )

    # Application Configuration
    port: int = Field(
        default=8080,
        description="Port to run the application on"
    )
    environment: str = Field(
        default="dev",
        description="Environment name (dev, test, prod)"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def auth0_issuer_url(self) -> str:
        """Get the Auth0 issuer URL, constructing it from domain if not explicitly set."""
        if self.auth0_issuer:
            return self.auth0_issuer
        return f"https://{self.auth0_domain}/"

    @property
    def auth0_jwks_url(self) -> str:
        """Get the Auth0 JWKS URL for fetching public keys."""
        return f"https://{self.auth0_domain}/.well-known/jwks.json"

    @property
    def database_url(self) -> str:
        """Construct the async PostgreSQL database URL."""
        password_part = f":{self.database_password}" if self.database_password else ""
        return (
            f"postgresql+asyncpg://{self.database_user}{password_part}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


_settings: Optional[Settings] = None


@lru_cache()
def get_settings() -> Settings:
    """
    Get the application settings singleton.

    This function uses lru_cache to ensure settings are loaded only once
    and reused across the application.

    Returns:
        Settings: The application settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
