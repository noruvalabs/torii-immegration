"""Geolocation and destination selection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from sqlalchemy import select

from torii_api.auth.deps import CurrentUserDep, SessionDep
from torii_api.db.models import CaseAction, IntakeDefinition, Jurisdiction, VisaCategory
from torii_api.services.geolocation import (
    detect_country_from_ip,
    get_application_types,
    get_destinations_excluding,
    get_nationalities,
    get_visa_types,
    resolve_country_meta,
)

router = APIRouter(prefix="/v1/geo", tags=["geolocation"])


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
    nationalities: list[DestinationOut]
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
    session: SessionDep = None,
) -> list[DestinationOut]:
    """List all supported destination countries (excluding user's current country if applicable)."""
    current_country = (getattr(current_user, "current_country", None) or "").upper()
    if session:
        live_jurisdictions = (
            await session.scalars(
                select(Jurisdiction).where(Jurisdiction.is_live.is_(True)).order_by(Jurisdiction.name)
            )
        ).all()
        if live_jurisdictions:
            destinations = []
            for j in live_jurisdictions:
                if j.code.upper() == current_country and len(live_jurisdictions) > 1:
                    continue
                destinations.append(resolve_country_meta(j.code, j.name))
            return [DestinationOut(**d) for d in destinations]

    destinations = get_destinations_excluding(current_country or "JP")
    return [DestinationOut(**d) for d in destinations]


@router.get("/visa-types", response_model=list[VisaTypeOut])
async def list_visa_types(
    destination: str | None = None,
    session: SessionDep = None,
) -> list[VisaTypeOut]:
    """List supported visa types, dynamically tailored if destination is given."""
    if destination and session:
        jurisdiction = await session.scalar(
            select(Jurisdiction).where(Jurisdiction.code == destination.upper())
        )
        if jurisdiction:
            categories = await session.scalars(
                select(VisaCategory)
                .where(VisaCategory.jurisdiction_id == jurisdiction.id)
                .where(VisaCategory.is_live.is_(True) | VisaCategory.research_enabled.is_(True))
                .order_by(VisaCategory.code)
            )
            cat_list = list(categories.all())
            if cat_list:
                result = []
                seen_codes = set()
                for c in cat_list:
                    if c.code in seen_codes:
                        continue
                    seen_codes.add(c.code)
                    desc = (
                        "Employment or business activities"
                        if c.code in ("work", "h1b")
                        else "Study at an educational institution"
                        if c.code in ("student", "f1")
                        else "Short-term stay for tourism or visiting"
                        if c.code in ("tourist", "b1b2")
                        else c.name
                    )
                    result.append(VisaTypeOut(code=c.code, name=c.name, description=desc))
                return result

    visa_types = get_visa_types()
    return [VisaTypeOut(**vt) for vt in visa_types]


@router.get("/nationalities", response_model=list[DestinationOut])
async def list_nationalities() -> list[DestinationOut]:
    """List all supported nationalities (country of origin)."""
    nationalities = get_nationalities()
    return [DestinationOut(**n) for n in nationalities]


@router.get("/application-types", response_model=list[ApplicationTypeOut])
async def list_application_types(
    destination: str | None = None,
    visa_type: str | None = None,
    session: SessionDep = None,
) -> list[ApplicationTypeOut]:
    """List application types, dynamically tailored if destination and visa_type are given."""
    if destination and session:
        jurisdiction = await session.scalar(
            select(Jurisdiction).where(Jurisdiction.code == destination.upper())
        )
        if jurisdiction:
            v_code = (visa_type or "").lower().strip()

            # Check if a specific visa category was requested
            visa_cat = None
            if v_code:
                visa_cat = await session.scalar(
                    select(VisaCategory)
                    .where(VisaCategory.jurisdiction_id == jurisdiction.id)
                    .where(VisaCategory.code == v_code)
                )

            # Query actions associated with this visa category
            action_list: list[CaseAction] = []
            if visa_cat:
                intake_actions = await session.scalars(
                    select(CaseAction)
                    .join(IntakeDefinition, IntakeDefinition.case_action_id == CaseAction.id)
                    .where(IntakeDefinition.jurisdiction_id == jurisdiction.id)
                    .where(IntakeDefinition.visa_category_id == visa_cat.id)
                    .distinct()
                )
                action_list = list(intake_actions.all())

            # Fallback to jurisdiction actions with statutory domain filtering
            if not action_list:
                actions = await session.scalars(
                    select(CaseAction)
                    .where(CaseAction.jurisdiction_id == jurisdiction.id)
                    .where(CaseAction.is_live.is_(True) | CaseAction.research_enabled.is_(True))
                    .order_by(CaseAction.code)
                )
                action_list = list(actions.all())

                # Apply domain rules:
                # 1. Tourist / Short-term / Visitor visas only support New Visa (Entry Visa)
                if v_code in ("tourist", "visitor", "b1b2", "short_term"):
                    action_list = [a for a in action_list if a.code in ("new", "new_application")]
                # 2. Permanent Resident only supports Permanent Residence Application
                elif v_code in ("permanent_resident", "pr", "ilr"):
                    action_list = [a for a in action_list if a.code in ("new", "new_application")]

            if action_list:
                result = []
                seen_codes = set()
                has_new = any(a.code == "new" for a in action_list)
                for a in action_list:
                    if a.code == "new_application" and has_new:
                        continue
                    if a.code in seen_codes:
                        continue
                    seen_codes.add(a.code)

                    name = a.name
                    desc = a.name
                    if v_code in ("permanent_resident", "pr", "ilr"):
                        name = "Permanent Residence Application"
                        desc = "Apply for permanent resident status (永住許可申請)"
                    elif v_code in ("tourist", "visitor", "b1b2"):
                        name = "Tourist / Entry Visa"
                        desc = "First-time short-term entry visa application"
                    elif a.code in ("new", "new_application"):
                        name = "New Visa"
                        desc = (
                            "First-time application / Certificate of Eligibility (COE)"
                            if jurisdiction.code == "JP"
                            else "First-time visa application"
                        )
                    elif a.code == "renewal":
                        name = "Renewal / Extension"
                        desc = "Extend or renew existing visa before expiration"
                    elif a.code == "change_of_status":
                        name = "Change of status"
                        desc = "Switch to a different visa status inside the country"

                    result.append(ApplicationTypeOut(code=a.code, name=name, description=desc))
                return result

    app_types = get_application_types()
    return [ApplicationTypeOut(**at) for at in app_types]


@router.get("/all", response_model=GeoDataOut)
async def get_all_geo_data(
    request: Request,
    session: SessionDep = None,
) -> GeoDataOut:
    """Get all geolocation data in one call (for frontend initialization)."""
    geo = await detect_country_from_ip(request)

    destinations = []
    if session:
        live_jurisdictions = (
            await session.scalars(
                select(Jurisdiction).where(Jurisdiction.is_live.is_(True)).order_by(Jurisdiction.name)
            )
        ).all()
        for j in live_jurisdictions:
            destinations.append(resolve_country_meta(j.code, j.name))

    if not destinations:
        destinations = get_destinations_excluding(geo.country_code)

    nationalities = get_nationalities()
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
        nationalities=[DestinationOut(**n) for n in nationalities],
        visa_types=[VisaTypeOut(**vt) for vt in visa_types],
        application_types=[ApplicationTypeOut(**at) for at in app_types],
    )


class ResidenceIn(BaseModel):
    country_code: str


@router.put("/residence")
async def update_residence_country(
    payload: ResidenceIn,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> dict:
    """Update user's residence country (ISO alpha-2 code or country name)."""
    from sqlalchemy import update as sa_update

    from torii_api.db.models import User

    country_code = payload.country_code.strip()
    if len(country_code) < 2:
        raise HTTPException(status_code=400, detail="country_code is required")

    await session.execute(
        sa_update(User)
        .where(User.id == current_user.id)
        .values(current_country=country_code.upper() if len(country_code) == 2 else country_code)
    )
    await session.flush()

    return {
        "message": "Residence country updated",
        "country_code": country_code.upper() if len(country_code) == 2 else country_code,
    }
