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

    # Run seed on service startup. Off by default; enable in dev/staging to auto-populate
    # jurisdictions, visa categories, and workflows on first boot.
    seed_on_startup: bool = False

    # --- Background scheduler / task queue (arq over Redis) --------------------
    # The API enqueues jobs here; a separate `arq` worker consumes them and runs the
    # cron schedule. The API degrades gracefully when Redis is absent (enqueue no-ops
    # with a warning), so the request path never hard-depends on the queue.
    redis_url: str = "redis://localhost:6379/0"
    # Outbox poll cadence (seconds) — how often the worker drains unprocessed events.
    outbox_poll_interval_seconds: int = 10
    # Lead time (days) before a recorded renewal date at which reminders are sent (US-19).
    renewal_reminder_lead_days: int = 30

    # --- Auth (JWT bearer tokens for applicants and staff — US-20.4, US-30) ----
    # Dev default only; production must set TORII_JWT_SECRET_KEY from a secret store.
    jwt_secret_key: str = "dev-only-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # --- Email verification / password-reset tokens ---------------------------
    email_verification_token_expire_minutes: int = 60 * 24  # 24 hours
    password_reset_token_expire_minutes: int = 60  # 1 hour

    # --- SMTP (email delivery — verification, password reset) -----------------
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@torii.app"
    smtp_from_name: str = "Torii"
    smtp_tls: bool = True

    # --- Base URL for building email links ------------------------------------
    app_base_url: str = "http://localhost:3000"

    # --- AI service (OPS scraper, assistant chat) ------------------------------
    ai_service_url: str = "http://localhost:8001"
    # Comma-separated list of jurisdiction codes to scrape daily (US-25, US-26).
    scrape_jurisdictions: str = "JP,US"
    # Service-to-service token for authenticated AI→API calls.
    service_token: str = ""

    # --- Content packs (docs/jurisdictions/*.yml) -------------------------------
    # Empty = auto-detect monorepo docs/jurisdictions. Override for deploys that
    # mount packs outside the package tree.
    jurisdictions_dir: str = ""

    # When true, GET /v1/cases/{id}/packet requires a completed payment
    # entitlement (US-22.2). Off in unit tests unless explicitly enabled.
    require_packet_entitlement: bool = True

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
