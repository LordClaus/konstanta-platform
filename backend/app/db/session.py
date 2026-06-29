"""Async engine + session factory.

A lazily-initialized engine/sessionmaker pair, exposed through the
`get_session()` FastAPI dependency. Keeping construction lazy (rather than at
import time) lets the test suite point the engine at a throwaway SQLite file
before the first session is ever requested.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None) -> AsyncEngine:
    """(Re)build the engine and session factory. Returns the new engine.

    SQLite and PostgreSQL need different connect args, so we branch on the URL:
    SQLite (tests/local) disables the same-thread check; PostgreSQL (prod) turns
    on pool pre-ping to recycle connections dropped by the server.
    """
    global _engine, _sessionmaker
    url = database_url or get_settings().database_url
    if url.startswith("sqlite"):
        _engine = create_async_engine(
            url, echo=False, future=True, connect_args={"check_same_thread": False}
        )
    else:
        _engine = create_async_engine(url, echo=False, future=True, pool_pre_ping=True)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        init_engine()
    assert _engine is not None
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session.

    Commits on a clean exit, rolls back on any exception, always closes.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
