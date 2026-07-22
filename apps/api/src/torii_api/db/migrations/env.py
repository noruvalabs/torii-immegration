"""Alembic environment — async engine, SQLite- and Postgres-aware.

Drives migrations through the async engine via ``run_sync``. ``render_as_batch`` is enabled on
SQLite so future ALTER-heavy migrations work (SQLite rebuilds tables in a batch); on Postgres
it is a harmless no-op. The URL comes from Alembic's config (set by :mod:`torii_api.db.migrator`
or ``alembic.ini``); the CLI falls back to ``TORII_DATABASE_URL`` via settings.
"""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import models so Base.metadata is populated (autogenerate / reference).
import torii_api.db.models  # noqa: F401
from torii_api.db.base import Base

config = context.config
target_metadata = Base.metadata


def _do_run_migrations(connection: Connection) -> None:
    is_sqlite = connection.dialect.name == "sqlite"
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=is_sqlite,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {})
    if not section.get("sqlalchemy.url"):
        # CLI convenience: fall back to the configured database (TORII_DATABASE_URL).
        from torii_api.config import get_settings
        from torii_api.db.engine import to_async_url

        section["sqlalchemy.url"] = to_async_url(get_settings().database_url)
    engine = async_engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():  # pragma: no cover - offline SQL generation unused
    raise SystemExit("offline migrations are not supported for this project")
run_migrations_online()
