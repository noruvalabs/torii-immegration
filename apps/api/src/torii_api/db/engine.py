"""Async engine + session factory, with driver coercion for SQLite and Postgres.

One URL, two engines: a plain ``sqlite://`` or ``postgresql://`` (or ``postgres://``) URL is
rewritten to its async driver (``+aiosqlite`` / ``+asyncpg``) so nothing downstream — the app,
the worker, or Alembic — needs to know which database is in play.
"""

from __future__ import annotations

import os

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Postgres pool defaults, sized for the 1 GB deployment host. Override per-process via the
# environment if this ever runs somewhere with room to spare.
DEFAULT_POOL_SIZE = int(os.getenv("TORII_DB_POOL_SIZE", "10"))
DEFAULT_MAX_OVERFLOW = int(os.getenv("TORII_DB_MAX_OVERFLOW", "5"))
DEFAULT_POOL_TIMEOUT_SECONDS = float(os.getenv("TORII_DB_POOL_TIMEOUT", "30"))
DEFAULT_POOL_RECYCLE_SECONDS = int(os.getenv("TORII_DB_POOL_RECYCLE", "1800"))


def to_async_url(database_url: str) -> str:
    """Coerce a database URL to its async driver form and canonicalize relative SQLite paths.

    Already-qualified URLs (``sqlite+aiosqlite://``, ``postgresql+asyncpg://``) pass through.
    """
    # Canonicalize relative SQLite paths so whether the process starts in root or apps/api,
    # it always binds to apps/api/torii.db.
    if "sqlite" in database_url and ":memory:" not in database_url:
        prefix, rest = database_url.split("://", 1)
        cleaned = rest.lstrip("/")
        if cleaned.startswith("./"):
            cleaned = cleaned[2:]
        if not os.path.isabs(cleaned):
            from pathlib import Path

            api_dir = Path(__file__).resolve().parents[3]  # apps/api
            canonical = (api_dir / cleaned).resolve().as_posix()
            driver = "sqlite+aiosqlite" if "+" not in prefix else prefix
            return f"{driver}:///{canonical}"

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
    # SQLite gets WAL mode and timeout for high concurrency; Postgres benefits from pre-ping.
    if url.startswith("sqlite"):
        engine = create_async_engine(url, connect_args={"timeout": 30.0})

        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        return engine
    # Bounded pool. The deployed Postgres runs with max_connections=40 (see
    # infra/compose/docker-compose.yml) because each idle backend costs several MB of RSS on
    # a small host, so the pools have to be sized to fit rather than left at SQLAlchemy's
    # default 5+10 per process — which, across the api and the worker, can outgrow the server
    # and turn a traffic spike into "FATAL: sorry, too many clients already".
    #
    # 10+5 x {api, worker} = 30 worst case, leaving headroom for migrations, psql, and the
    # superuser reserve. `pool_recycle` keeps connections under any idle timeout upstream.
    return create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=DEFAULT_POOL_SIZE,
        max_overflow=DEFAULT_MAX_OVERFLOW,
        # Fail the request rather than pile up waiters behind an exhausted pool.
        pool_timeout=DEFAULT_POOL_TIMEOUT_SECONDS,
        pool_recycle=DEFAULT_POOL_RECYCLE_SECONDS,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
