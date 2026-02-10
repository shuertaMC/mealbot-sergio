from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mealbot.config import settings

engine = create_async_engine(settings.database_url, echo=False, future=True) if settings.database_url else None

async_session = (
    async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    if engine
    else None
)


async def get_session():
    if async_session is None:
        raise RuntimeError("Database not configured")
    async with async_session() as session:
        yield session
