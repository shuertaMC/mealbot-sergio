import pytest
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from mealbot.auth import require_auth, _AuthError, auth_error_handler
from mealbot.cors import setup_cors
from mealbot.db import get_session
from mealbot import org


def _create_test_app(auth_user=None, session_mock=None):
    """Create a test FastAPI app with overridden dependencies."""
    app = FastAPI()
    setup_cors(app)
    app.add_exception_handler(_AuthError, auth_error_handler)
    app.include_router(org.router)

    if auth_user is not None:
        app.dependency_overrides[require_auth] = lambda: auth_user

    if session_mock is not None:
        async def _override_session():
            yield session_mock
        app.dependency_overrides[get_session] = _override_session

    return app


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def authenticated_user():
    """A fake authenticated user payload."""
    return {"sub": "auth0|123", "email": "admin@test.com"}


@pytest.fixture
def test_app(authenticated_user, mock_session):
    """Create a test app with auth and DB overridden."""
    return _create_test_app(auth_user=authenticated_user, session_mock=mock_session)


@pytest.fixture
def unauth_app(mock_session):
    """Create a test app without auth override (will require real auth)."""
    return _create_test_app(session_mock=mock_session)


@pytest.fixture
async def client(test_app):
    """Async HTTP client for testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def unauth_client(unauth_app):
    """Async HTTP client that does NOT have auth overridden."""
    transport = ASGITransport(app=unauth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
