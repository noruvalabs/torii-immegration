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
    Strips ``sslmode`` query parameter which asyncpg rejects in favor of connect_args.
    """
    clean_url = database_url
    if "sslmode=" in clean_url:
        import re

        clean_url = re.sub(r"[?&]sslmode=[^&]+", "", clean_url)
        clean_url = clean_url.replace("?&", "?").rstrip("?")

    # Canonicalize relative SQLite paths (e.g. ./torii.db or torii.db) so whether the process
    # starts in root or apps/api, it always binds to apps/api/torii.db without corrupting absolute
    # temporary test paths on POSIX (e.g. sqlite:////tmp/...) or Windows (e.g. sqlite:///C:/...).
    if "sqlite" in clean_url and ":memory:" not in clean_url:
        prefix, rest = clean_url.split("://", 1)
        # Check if the path is explicitly relative
        stripped = rest.lstrip("/")
        has_win_drive = len(stripped) >= 2 and stripped[1] == ":" and stripped[0].isalpha()
        is_posix_abs = rest.startswith("//")
        is_relative = (
            not is_posix_abs
            and not has_win_drive
            and (
                rest.startswith("/./")
                or rest.startswith("./")
                or not rest.startswith("/")
                or stripped == "torii.db"
                or stripped.startswith("./")
            )
        )
        if is_relative:
            cleaned = stripped
            if cleaned.startswith("./"):
                cleaned = cleaned[2:]
            from pathlib import Path

            api_dir = Path(__file__).resolve().parents[3]  # apps/api
            canonical = (api_dir / cleaned).resolve().as_posix()
            driver = "sqlite+aiosqlite" if "+" not in prefix else prefix
            return f"{driver}:///{canonical}"

    if "+" in clean_url.split("://", 1)[0]:
        return clean_url
    if clean_url.startswith("sqlite://"):
        return "sqlite+aiosqlite://" + clean_url[len("sqlite://") :]
    if clean_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + clean_url[len("postgresql://") :]
    if clean_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + clean_url[len("postgres://") :]
    return clean_url


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

    connect_args: dict[str, object] = {}
    if "asyncpg" in url:
        # statement_cache_size=0 is required for connection poolers (e.g. Supabase Supavisor)
        # to prevent prepared statement collisions.
        connect_args["statement_cache_size"] = int(os.getenv("TORII_DB_STATEMENT_CACHE_SIZE", "0"))
        if (
            "sslmode=require" in database_url
            or "ssl=require" in database_url
            or "supabase.com" in database_url
            or "supabase.co" in database_url
        ):
            connect_args["ssl"] = "require"

    return create_async_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=DEFAULT_POOL_SIZE,
        max_overflow=DEFAULT_MAX_OVERFLOW,
        # Fail the request rather than pile up waiters behind an exhausted pool.
        pool_timeout=DEFAULT_POOL_TIMEOUT_SECONDS,
        pool_recycle=DEFAULT_POOL_RECYCLE_SECONDS,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
