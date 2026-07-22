"""Scalar API-reference UI — the API's single docs surface (served at ``/docs``).

The spec reference is document-relative (``openapi.json``, no leading slash) so it resolves
directly (``/docs`` → ``/openapi.json``) and behind an edge prefix (``/api/docs`` →
``/api/openapi.json``) alike.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference


def build_docs_router(*, title: str) -> APIRouter:
    """Router serving the Scalar UI at ``/docs``, hidden from the schema itself."""
    router = APIRouter()

    @router.get("/docs", include_in_schema=False)
    async def scalar_docs() -> HTMLResponse:
        return get_scalar_api_reference(openapi_url="openapi.json", title=title)

    return router
