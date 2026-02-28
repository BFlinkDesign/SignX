"""
database.py — Async SQLAlchemy engine + SQLite session management for 500IQ.

Follows the SignX-Intel/storage/database.py pattern (async context manager,
FastAPI dependency injection) but uses aiosqlite instead of asyncpg.

The SQLite file lives alongside the service: ./signx_500iq.db
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

DB_PATH = os.getenv("IQ_DB_PATH", "signx_500iq.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("IQ_DEBUG", "").lower() in ("1", "true"),
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


async def init_db() -> None:
    """Create all tables on first run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Scoped session with auto commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends() injection."""
    async with get_db() as session:
        yield session
