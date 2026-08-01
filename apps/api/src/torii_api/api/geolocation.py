"""Geolocation and destination selection endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.session import get_session
from torii_api.services.geolocation import (
    detect_country_from_ip,
    get_application_types,
    get_destinations_excluding,
    get_visa_types,
)

router = APIRouter(prefix="/v1/geo", tags=["geolocation"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── Response schemas ──────────────────────────────────────────────────────────


class GeoLocationOut(BaseModel):
    ip: str
    country_code: str
    country_name: str
    city: str | None = None
    region: str | None = None
    is_japan: bool = False
    timezone: str | None = None


class DestinationOut(BaseModel):
    code: str
    name: str
    currency: str
    flag: str


class VisaTypeOut(BaseModel):
    code: str
    name: str
    description: str


class ApplicationTypeOut(BaseModel):
    code: str
    name: str
    description: str


class GeoDataOut(BaseModel):
    detected_country: GeoLocationOut
    destinations: list[DestinationOut]
    visa_types: list[VisaTypeOut]
    application_types: list[ApplicationTypeOut]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/detect", response_model=GeoLocationOut)
async def detect_country(
    request: Request,
) -> GeoLocationOut:
    """Auto-detect user's country from IP address."""
    geo = await detect_country_from_ip(request)
    return GeoLocationOut(
        ip=geo.ip,
        country_code=geo.country_code,
        country_name=geo.country_name,
        city=geo.city,
        region=geo.region,
        is_japan=geo.is_japan,
        timezone=geo.timezone,
    )


@router.get("/destinations", response_model=list[DestinationOut])
async def list_destinations(
    current_user: CurrentUserDep,
) -> list[DestinationOut]:
    """List all supported destination countries (excluding user's current country)."""
    # Get user's current country from profile
    current_country = getattr(current_user, "current_country", None)
    if not current_country:
        # Default to Japan if not set
        current_country = "JP"

    destinations = get_destinations_excluding(current_country)
    return [DestinationOut(**d) for d in destinations]


@router.get("/visa-types", response_model=list[VisaTypeOut])
async def list_visa_types() -> list[VisaTypeOut]:
    """List all supported visa types."""
    visa_types = get_visa_types()
    return [VisaTypeOut(**vt) for vt in visa_types]


@router.get("/application-types", response_model=list[ApplicationTypeOut])
async def list_application_types() -> list[ApplicationTypeOut]:
    """List all application types (new/renewal)."""
    app_types = get_application_types()
    return [ApplicationTypeOut(**at) for at in app_types]


@router.get("/all", response_model=GeoDataOut)
async def get_all_geo_data(
    request: Request,
    current_user: CurrentUserDep,
) -> GeoDataOut:
    """Get all geolocation data in one call (for frontend initialization)."""
    geo = await detect_country_from_ip(request)

    # Get destinations excluding user's current country
    current_country = getattr(current_user, "current_country", None) or geo.country_code
    destinations = get_destinations_excluding(current_country)
    visa_types = get_visa_types()
    app_types = get_application_types()

    return GeoDataOut(
        detected_country=GeoLocationOut(
            ip=geo.ip,
            country_code=geo.country_code,
            country_name=geo.country_name,
            city=geo.city,
            region=geo.region,
            is_japan=geo.is_japan,
            timezone=geo.timezone,
        ),
        destinations=[DestinationOut(**d) for d in destinations],
        visa_types=[VisaTypeOut(**vt) for vt in visa_types],
        application_types=[ApplicationTypeOut(**at) for at in app_types],
    )


@router.put("/residence")
async def update_residence_country(
    current_user: CurrentUserDep,
    session: SessionDep,
    country_code: str,
) -> dict:
    """Update user's residence country (if they want to change from auto-detected)."""
    from sqlalchemy import update

    await session.execute(
        update(type(current_user))
        .where(type(current_user).id == current_user.id)
        .values(current_country=country_code)
    )
    await session.flush()

    return {"message": "Residence country updated", "country_code": country_code}
