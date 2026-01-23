"""Pytest configuration and fixtures for tests."""

import asyncio
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.config import get_settings


# Get settings for test database connection
settings = get_settings()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create a test database engine for each test.

    Uses in-memory SQLite database for testing to avoid requiring
    a PostgreSQL instance. SQLite is sufficient for testing the API
    logic and database operations.

    Note: Using function scope to ensure each test gets a fresh database.
    """
    # Use in-memory SQLite for testing with shared cache for connection reuse
    # StaticPool ensures the same connection is reused for all operations
    test_database_url = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(
        test_database_url,
        poolclass=StaticPool,
        echo=False,
        # SQLite-specific settings for compatibility
        connect_args={"check_same_thread": False},
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables and dispose
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for testing.

    Each test gets a fresh session with tables already created.
    """
    # Create a new session for the test
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session
        # Try to commit, but rollback on error
        try:
            await session.commit()
        except Exception:
            await session.rollback()
