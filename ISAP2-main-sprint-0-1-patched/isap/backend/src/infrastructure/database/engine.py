from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.settings import settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Create database engine lazily.

    Importing domain/repository modules must not require a running DB driver or a
    configured DATABASE_URL. The engine is created only when a real DB session is
    requested by an API endpoint, migration script, or integration test.
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
    )


@lru_cache(maxsize=1)
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


def async_session_factory() -> AsyncSession:
    """Backward-compatible callable used by existing dependencies."""
    return get_async_session_factory()()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
