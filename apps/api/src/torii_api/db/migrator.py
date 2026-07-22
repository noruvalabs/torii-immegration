"""Programmatic Alembic — the same upgrade path for startup, tests, and the CLI.

``migrate_on_startup`` calls :func:`apply_migrations` at boot. Alembic's env drives the async
engine via ``asyncio.run`` internally, so callers already inside an event loop (the FastAPI
lifespan) must invoke it off the loop thread — see :func:`apply_migrations_in_thread`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

from torii_api.db.engine import to_async_url

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def alembic_config(database_url: str) -> Config:
    """Build an Alembic config bound to the packaged migration scripts and ``database_url``."""
    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", to_async_url(database_url))
    return cfg


def apply_migrations(database_url: str) -> None:
    """Upgrade the database to ``head`` (blocking; must not run inside an event loop)."""
    command.upgrade(alembic_config(database_url), "head")


async def apply_migrations_in_thread(database_url: str) -> None:
    """Upgrade to ``head`` from within an event loop, off the loop thread."""
    await asyncio.to_thread(apply_migrations, database_url)
