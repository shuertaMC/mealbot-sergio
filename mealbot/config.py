import os

# Load .env file in non-production environments via python-dotenv.
# python-dotenv is optional — it may not be installed in production.
if os.getenv("FLASK_ENV") != "production":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def get_port():
    """Get the server port. Defaults to 8080."""
    return int(os.getenv("PORT", "8080"))


def get_database_url():
    """Get the DATABASE_URL for PostgreSQL connection."""
    return os.getenv("DATABASE_URL", "")


def get_auth0_settings():
    """Get Auth0 configuration settings."""
    return {
        "domain": os.getenv("AUTH0_DOMAIN", "mealbot.auth0.com"),
        "audience": os.getenv("AUTH0_AUDIENCE", "https://mealbot-2.herokuapp.com/"),
        "issuer": os.getenv("AUTH0_ISSUER", "https://mealbot.auth0.com/"),
        "algorithms": os.getenv("AUTH0_ALGORITHMS", "RS256"),
        "jwks_url": os.getenv(
            "AUTH0_JWKS_URL",
            "https://mealbot.auth0.com/.well-known/jwks.json",
        ),
    }


def get_mailgun_config():
    """Get Mailgun configuration settings."""
    return {
        "smtp_login": os.getenv("MAILGUN_SMTP_LOGIN", ""),
        "domain": os.getenv("MAILGUN_DOMAIN", ""),
        "api_key": os.getenv("MAILGUN_API_KEY", ""),
    }
