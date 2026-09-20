"""Test fixtures: an app wired to a throwaway in-memory SQLite database.

Tables are created directly from ``Base.metadata`` (no Alembic needed for unit tests), the
session factory is pre-seeded on ``app.state`` before startup, and the arq pool is stubbed to
``None`` so tests never touch Redis. A single shared in-memory connection is used so every
session sees the same schema.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from torii_api.db.base import Base
from torii_api.db.engine import create_session_factory
from torii_api.main import create_app


@pytest.fixture(autouse=True)
def _prevent_real_emails_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no tests ever attempt real SMTP delivery to external servers, and keep unit tests fast."""
    monkeypatch.setattr("torii_api.auth.email.send_email", lambda **kwargs: True)
    try:
        monkeypatch.setattr("torii_api.api.auth.send_email", lambda **kwargs: True)
    except AttributeError:
        pass
    from torii_api.config import get_settings

    monkeypatch.setattr(get_settings(), "require_email_verification", False)
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", False)


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.arq_pool = None  # never connect to Redis in tests
    app.state.testing = True

    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
