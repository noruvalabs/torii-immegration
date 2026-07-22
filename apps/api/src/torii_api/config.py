"""Application settings, loaded from the environment (prefix ``TORII_``).

Defaults are local-development only and never real secrets. Production values arrive from the
environment / secret store at deploy time. The default database is a local **SQLite** file, so
the API runs with zero infrastructure; point ``TORII_DATABASE_URL`` at Postgres to switch.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Torii API service."""

    model_config = SettingsConfigDict(
        env_prefix="TORII_",
        env_file=".env",
        extra="ignore",
    )

    service_name: str = "torii-api"
    log_level: str = "INFO"

    # Serve the Scalar API-reference UI (/docs) and the OpenAPI spec (/openapi.json).
    docs_enabled: bool = True

    # System of record. SQLite by default (zero-setup local dev — creates ./torii.db);
    # set TORII_DATABASE_URL=postgresql://user:pass@host:5432/torii for Postgres. The
    # async driver (aiosqlite / asyncpg) is derived automatically — see db.engine.
    database_url: str = "sqlite:///./torii.db"

    # Run Alembic migrations on service startup. Off by default (the CLI / entrypoint
    # applies them explicitly); handy to enable in dev/staging containers via env.
    migrate_on_startup: bool = False

    # --- Background scheduler / task queue (arq over Redis) --------------------
    # The API enqueues jobs here; a separate `arq` worker consumes them and runs the
    # cron schedule. The API degrades gracefully when Redis is absent (enqueue no-ops
    # with a warning), so the request path never hard-depends on the queue.
    redis_url: str = "redis://localhost:6379/0"
    # Outbox poll cadence (seconds) — how often the worker drains unprocessed events.
    outbox_poll_interval_seconds: int = 10
    # Lead time (days) before a recorded renewal date at which reminders are sent (US-19).
    renewal_reminder_lead_days: int = 30

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
