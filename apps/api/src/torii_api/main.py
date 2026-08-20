"""Application factory and uvicorn entrypoint for the Torii API service."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from torii_api import __version__
from torii_api.api.admin import router as admin_router
from torii_api.api.admin_ops import router as admin_ops_router
from torii_api.api.auth import router as auth_router
from torii_api.api.case_workflow import router as case_workflow_router
from torii_api.api.cases import router as cases_router
from torii_api.api.corridors import router as corridors_router
from torii_api.api.credits import router as credits_router
from torii_api.api.docs import build_docs_router
from torii_api.api.geolocation import router as geo_router
from torii_api.api.health import router as health_router
from torii_api.api.jurisdictions import router as jurisdictions_router
from torii_api.api.payments import router as payments_router
from torii_api.api.wallet import router as wallet_router
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

        if settings.seed_on_startup:
            from torii_api.management.seed import seed

            await seed()
            log.info("api.seeded")

        if not getattr(app.state, "engine", None):
            app.state.engine = create_engine(settings.database_url)
        if not getattr(app.state, "session_factory", None):
            app.state.session_factory = create_session_factory(app.state.engine)

        # Best-effort task queue: present if Redis is reachable, None otherwise.
        if not hasattr(app.state, "arq_pool"):
            from torii_api.worker.queue import build_pool

            app.state.arq_pool = await build_pool(settings.redis_url)

        drainer_task = None
        is_test = (
            getattr(app.state, "testing", False)
            or getattr(app.state, "disable_drainer", False)
            or (":memory:" in settings.database_url)
            or (settings.database_url == "sqlite+aiosqlite://")
        )
        if not is_test:
            from torii_api.worker.scheduler import poll_outbox

            async def _in_process_outbox_drainer() -> None:
                ctx = {"session_factory": app.state.session_factory}
                while True:
                    try:
                        await poll_outbox(ctx)
                    except asyncio.CancelledError:
                        break
                    except Exception as exc:  # noqa: BLE001
                        log.warning("outbox.in_process_drain_error", error=str(exc))
                    await asyncio.sleep(2)

            drainer_task = asyncio.create_task(_in_process_outbox_drainer())
            log.info("api.in_process_outbox_drainer_started")

        yield

        log.info("api.shutdown", service=settings.service_name)
        if drainer_task is not None:
            drainer_task.cancel()
            try:
                await drainer_task
            except asyncio.CancelledError:
                pass
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
    app.include_router(corridors_router)
    app.include_router(cases_router)
    app.include_router(case_workflow_router)
    app.include_router(payments_router)
    app.include_router(geo_router)
    app.include_router(wallet_router)
    app.include_router(credits_router)
    app.include_router(admin_router)
    app.include_router(admin_ops_router)
    app.include_router(auth_router)
    return app


app = create_app()


def main() -> None:
    """Run the service under uvicorn (``python -m torii_api.main``)."""
    import uvicorn

    uvicorn.run("torii_api.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
