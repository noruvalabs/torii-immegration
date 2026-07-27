"""Health endpoint consumed by uptime probes and the reverse proxy."""

from fastapi import APIRouter
from pydantic import BaseModel

from torii_ai import __version__
from torii_ai.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", tags=["ops"])
async def health() -> HealthResponse:
    """Liveness/readiness signal. Cheap and dependency-free by design."""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.service_name, version=__version__)
