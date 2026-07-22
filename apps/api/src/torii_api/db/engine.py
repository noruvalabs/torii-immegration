"""Async engine + session factory, with driver coercion for SQLite and Postgres.

One URL, two engines: a plain ``sqlite://`` or ``postgresql://`` (or ``postgres://``) URL is
rewritten to its async driver (``+aiosqlite`` / ``+asyncpg``) so nothing downstream — the app,
the worker, or Alembic — needs to know which database is in play.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def to_async_url(database_url: str) -> str:
    """Coerce a database URL to its async driver form.

    Already-qualified URLs (``sqlite+aiosqlite://``, ``postgresql+asyncpg://``) pass through.
    """
    if "+" in database_url.split("://", 1)[0]:
        return database_url
    if database_url.startswith("sqlite://"):
        return "sqlite+aiosqlite://" + database_url[len("sqlite://") :]
    if database_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + database_url[len("postgresql://") :]
    if database_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + database_url[len("postgres://") :]
    return database_url


def create_engine(database_url: str) -> AsyncEngine:
    """Create the async engine (``pool_pre_ping`` guards against stale connections)."""
    url = to_async_url(database_url)
    # SQLite gets no connection pool tuning; Postgres benefits from pre-ping.
    if url.startswith("sqlite"):
        return create_async_engine(url)
    return create_async_engine(url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
