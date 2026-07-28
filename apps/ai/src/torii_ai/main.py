"""Application factory and uvicorn entrypoint for the Torii AI service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from torii_ai import __version__
from torii_ai.api.chat import router as chat_router
from torii_ai.api.docs import build_docs_router
from torii_ai.api.health import router as health_router
from torii_ai.api.ocr import router as ocr_router
from torii_ai.api.ops import router as ops_router
from torii_ai.config import Settings, get_settings
from torii_ai.logging import configure_logging

APP_TITLE = "Torii AI"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI AI app: logging, health, chat, optional docs."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    log = structlog.get_logger()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        log.info(
            "ai.startup",
            service=settings.service_name,
            version=__version__,
            groq_configured=bool(settings.groq_api_key),
            tavily_configured=bool(settings.tavily_api_key),
        )
        app.state.settings = settings
        yield
        log.info("ai.shutdown", service=settings.service_name)

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
    app.include_router(chat_router)
    app.include_router(ocr_router)
    app.include_router(ops_router)
    return app


app = create_app()


def main() -> None:
    """Run the service under uvicorn (``python -m torii_ai.main``)."""
    import uvicorn

    uvicorn.run("torii_ai.main:app", host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
