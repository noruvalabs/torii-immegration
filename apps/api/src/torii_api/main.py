"""Application factory and uvicorn entrypoint for the Torii API service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from torii_api import __version__
from torii_api.api.auth import router as auth_router
from torii_api.api.docs import build_docs_router
from torii_api.api.health import router as health_router
from torii_api.api.jurisdictions import router as jurisdictions_router
from torii_api.config import Settings, get_settings
from torii_api.db.engine import create_engine, create_session_factory
from torii_api.logging import configure_logging

APP_TITLE = "Torii API"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app: configure logging, build the DB engine, wire routers.

    On startup (behind the lifespan) it builds the async engine + session factory, optionally
    applies migrations (``migrate_on_startup``), and best-effort connects the arq queue (a
    Redis outage never blocks startup). Tests may pre-seed ``app.state`` (e.g. a test engine)
    before startup; the lifespan only fills in what is missing.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    log = structlog.get_logger()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        log.info(
            "api.startup",
            service=settings.service_name,
            version=__version__,
            database=settings.database_url.split("://", 1)[0],
        )
        app.state.settings = settings

        if settings.migrate_on_startup:
            from torii_api.db.migrator import apply_migrations_in_thread

            await apply_migrations_in_thread(settings.database_url)
            log.info("api.migrations_applied")

        if not getattr(app.state, "engine", None):
            app.state.engine = create_engine(settings.database_url)
        if not getattr(app.state, "session_factory", None):
            app.state.session_factory = create_session_factory(app.state.engine)

        # Best-effort task queue: present if Redis is reachable, None otherwise.
        if not hasattr(app.state, "arq_pool"):
            from torii_api.worker.queue import build_pool

            app.state.arq_pool = await build_pool(settings.redis_url)

        yield

        log.info("api.shutdown", service=settings.service_name)
        pool = getattr(app.state, "arq_pool", None)
        if pool is not None:
            await pool.close()
        engine = getattr(app.state, "engine", None)
        if engine is not None:
            await engine.dispose()

    app = FastAPI(
        title=APP_TITLE,
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.include_router(health_router)
    if settings.docs_enabled:
        app.include_router(build_docs_router(title=APP_TITLE))
    app.include_router(jurisdictions_router)
    app.include_router(auth_router)
    return app


app = create_app()


def main() -> None:
    """Run the service under uvicorn (``python -m torii_api.main``)."""
    import uvicorn

    uvicorn.run("torii_api.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
