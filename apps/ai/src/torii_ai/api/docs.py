"""Scalar docs router factory."""

from __future__ import annotations

from fastapi import APIRouter
from scalar_fastapi import get_scalar_api_reference


def build_docs_router(*, title: str) -> APIRouter:
    router = APIRouter()

    @router.get("/docs", include_in_schema=False)
    async def docs() -> object:
        return get_scalar_api_reference(openapi_url="/openapi.json", title=title)

    return router
