"""FastAPI request-scoped database session dependency.

The engine and session factory are built once at startup and stashed on ``app.state``
(see :mod:`torii_api.main`). This dependency hands each request its own ``AsyncSession``,
committing on success and rolling back on error.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session; commit on success, roll back on exception."""
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
