"""Database connectivity and session management using SQLAlchemy 2.0 async."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.config import get_settings

# SQLAlchemy declarative base for ORM models
Base = declarative_base()

# Get settings to construct database URL
settings = get_settings()

# Create async engine with asyncpg driver
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "dev",  # Enable SQL logging in dev mode
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Default connection pool size
    max_overflow=10,  # Allow up to 10 overflow connections
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autoflush=False,  # Don't auto-flush before queries
    autocommit=False,  # Require explicit commits
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session for each request.

    The session is automatically closed after the request completes.
    This implements the recommended SQLAlchemy 2.0 async pattern with
    FastAPI dependency injection.

    Yields:
        AsyncSession: An async database session for the current request.

    Example:
        ```python
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
