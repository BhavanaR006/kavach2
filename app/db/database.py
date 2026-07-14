"""
Database engine setup and session management for Kavach 2.0.

Supports both SQLite (development) and PostgreSQL (production)
via the DATABASE_URL environment variable.

For Vercel deployment, uses /tmp for SQLite (writable in serverless).
"""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from app.config import settings


def _get_database_url() -> str:
    """Resolve the database URL, handling Vercel's read-only filesystem."""
    url = settings.DATABASE_URL
    # On Vercel/serverless, SQLite must use /tmp (only writable directory)
    is_serverless = (
        "VERCEL" in os.environ
        or "AWS_LAMBDA_FUNCTION_NAME" in os.environ
        or os.environ.get("ENVIRONMENT") == "vercel"
    )
    if is_serverless and "sqlite" in url:
        url = "sqlite+aiosqlite:////tmp/kavach.db"
    return url


# Create async engine based on DATABASE_URL
engine = create_async_engine(
    _get_database_url(),
    echo=(settings.ENVIRONMENT == "development"),
    pool_pre_ping=True,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def create_all_tables() -> None:
    """Create all database tables from registered models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides an async database session.

    Yields:
        AsyncSession: An active database session that auto-closes after use.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
