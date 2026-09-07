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
from torii_api.services.scope_availability import (
    available_actions,
    category_is_offerable,
    category_is_research_only,
    scope_is_live,
)

router = APIRouter(prefix="/v1/geo", tags=["geolocation"])

# Ordering the visa-type list by ``code`` is alphabetical by an internal handle, which put
# the two routes most applicants want — work and tourist — at the bottom of Japan's list.
# The conventional handles lead in the order people ask for them; everything a country
# publishes beyond them follows alphabetically by the name the applicant actually reads.
ROUTE_PRIORITY: tuple[str, ...] = (
    "work",
    "h1b",
    "student",
    "f1",
    "tourist",
    "visitor",
    "b1b2",
    "short_term",
    "dependent",
    "spouse",
    "permanent_resident",
    "pr",
    "ilr",
)


def _route_sort_key(category: VisaCategory) -> tuple[int, str]:
    try:
        rank = ROUTE_PRIORITY.index(category.code)
    except ValueError:
        rank = len(ROUTE_PRIORITY)
    return (rank, category.name.lower())


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
    # True when this route has no reviewed content pack and its requirements are read off
    # the government's own pages on demand. The applicant is told, rather than being left
    # to assume every route on the list is equally settled.
    is_research: bool = False


class ApplicationTypeOut(BaseModel):
    code: str
    name: str
    description: str
    is_research: bool = False


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
    session: SessionDep,
) -> list[DestinationOut]:
    """List all supported destination countries (excluding user's current country if applicable)."""
    current_country = (getattr(current_user, "current_country", None) or "").upper()
    if session:
        live_jurisdictions = (
            await session.scalars(
                select(Jurisdiction)
                .where(Jurisdiction.is_live.is_(True), Jurisdiction.is_enabled.is_(True))
                .order_by(Jurisdiction.name)
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
    session: SessionDep,
    destination: str | None = None,
) -> list[VisaTypeOut]:
    """List the routes an applicant can actually open a case on for this destination."""
    if destination and session:
        jurisdiction = await session.scalar(
            select(Jurisdiction).where(Jurisdiction.code == destination.upper())
        )
        if jurisdiction:
            categories = list(
                (
                    await session.scalars(
                        select(VisaCategory)
                        .where(VisaCategory.jurisdiction_id == jurisdiction.id)
                        .where(VisaCategory.is_enabled.is_(True))
                    )
                ).all()
            )
            # Every enabled procedure for the country, read once: a route is only worth
            # listing if at least one of them pairs with it into a scope ``scope_case``
            # will accept. Both lists are tens of rows at most.
            actions = list(
                (
                    await session.scalars(
                        select(CaseAction)
                        .where(CaseAction.jurisdiction_id == jurisdiction.id)
                        .where(CaseAction.is_enabled.is_(True))
                    )
                ).all()
            )

            result = []
            seen_codes = set()
            for c in sorted(categories, key=_route_sort_key):
                if c.code in seen_codes:
                    continue
                if not category_is_offerable(jurisdiction, c, actions):
                    continue
                seen_codes.add(c.code)
                result.append(
                    VisaTypeOut(
                        code=c.code,
                        name=c.name,
                        # Whatever this country's own page says about the route, or nothing.
                        # A generic line invented here only repeats what the name already
                        # carries — see the note on ``VisaCategory.description``.
                        description=c.description or "",
                        is_research=category_is_research_only(jurisdiction, c, actions),
                    )
                )
            # A known destination with nothing offerable returns nothing. Falling back to
            # the generic list here would offer routes this country has no rows for, and
            # every one of them would be refused at Start application.
            return result

    visa_types = get_visa_types()
    return [VisaTypeOut.model_validate(vt) for vt in visa_types]


@router.get("/nationalities", response_model=list[DestinationOut])
async def list_nationalities() -> list[DestinationOut]:
    """List all supported nationalities (country of origin)."""
    nationalities = get_nationalities()
    return [DestinationOut(**n) for n in nationalities]


@router.get("/application-types", response_model=list[ApplicationTypeOut])
async def list_application_types(
    session: SessionDep,
    destination: str | None = None,
    visa_type: str | None = None,
) -> list[ApplicationTypeOut]:
    """List the procedures available for a destination, or for one route within it.

    Given both a destination and a ``visa_type``, this is the applicant's offer: every
    procedure it returns forms a scope ``scope_case`` will accept.
    """
    if destination and session:
        jurisdiction = await session.scalar(
            select(Jurisdiction).where(Jurisdiction.code == destination.upper())
        )
        if jurisdiction:
            v_code = (visa_type or "").lower().strip()

            visa_cat = None
            action_list: list[CaseAction] = []

            if v_code:
                visa_cat = await session.scalar(
                    select(VisaCategory)
                    .where(VisaCategory.jurisdiction_id == jurisdiction.id)
                    .where(VisaCategory.code == v_code)
                    .where(VisaCategory.is_enabled.is_(True))
                )
                # A route the applicant cannot open a case on has no procedures to offer.
                if visa_cat is None:
                    return []

                # Procedures this route has a *published* intake for come first. A draft
                # intake definition is ops's work in progress, not an offer.
                intake_actions = await session.scalars(
                    select(CaseAction)
                    .where(CaseAction.jurisdiction_id == jurisdiction.id)
                    .where(CaseAction.is_enabled.is_(True))
                    .where(
                        CaseAction.id.in_(
                            select(IntakeDefinition.case_action_id)
                            .where(IntakeDefinition.jurisdiction_id == jurisdiction.id)
                            .where(IntakeDefinition.visa_category_id == visa_cat.id)
                            .where(IntakeDefinition.is_live.is_(True))
                        )
                    )
                    .order_by(CaseAction.code)
                )
                action_list = list(intake_actions.all())

                # Fallback to jurisdiction actions if no specific intake actions
                if not action_list:
                    actions = await session.scalars(
                        select(CaseAction)
                        .where(CaseAction.jurisdiction_id == jurisdiction.id)
                        .where(CaseAction.is_enabled.is_(True))
                        .order_by(CaseAction.code)
                    )
                    action_list = list(actions.all())

                # Both branches pass through the one availability test ``scope_case``
                # applies, so a procedure that would be refused at Start application is
                # never listed. This is the path the applicant flow takes.
                action_list = available_actions(jurisdiction, visa_cat, action_list)
            else:
                # Destination only. With no route named there is no pair to test, so this
                # stays the per-row listing it has always been: switched on, and backed by
                # a pack or by research.
                actions = await session.scalars(
                    select(CaseAction)
                    .where(CaseAction.jurisdiction_id == jurisdiction.id)
                    .where(CaseAction.is_enabled.is_(True))
                    .where(CaseAction.is_live.is_(True) | CaseAction.research_enabled.is_(True))
                    .order_by(CaseAction.code)
                )
                action_list = list(actions.all())

            # Always apply statutory domain rules to filter valid actions:
            # 1. Tourist / Short-term / Visitor visas only support New Visa (Entry Visa)
            if v_code in ("tourist", "visitor", "b1b2", "short_term"):
                action_list = [a for a in action_list if a.code in ("new", "new_application")]
            # 2. Permanent Resident only supports Permanent Residence Application
            elif v_code in ("permanent_resident", "pr", "ilr"):
                action_list = [a for a in action_list if a.code in ("new", "new_application")]

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
                desc = a.description or ""
                if v_code in ("permanent_resident", "pr", "ilr"):
                    name = "Permanent Residence Application"
                    desc = "Apply for permanent resident status (永住許可申請)"
                elif v_code in ("tourist", "visitor", "b1b2"):
                    name = "Tourist / Entry Visa"
                    desc = "First-time short-term entry visa application"
                # The pack's own wording wins over these generic lines, which stay as
                # the fallback for actions that predate the description column.
                elif a.code in ("new", "new_application"):
                    name = "New Visa"
                    desc = a.description or (
                        "First-time application / Certificate of Eligibility (COE)"
                        if jurisdiction.code == "JP"
                        else "First-time visa application"
                    )
                elif a.code == "renewal":
                    name = "Renewal / Extension"
                    desc = a.description or "Extend or renew existing visa before expiration"
                elif a.code == "change_of_status":
                    name = "Change of status"
                    desc = a.description or "Switch to a different visa status inside the country"

                result.append(
                    ApplicationTypeOut(
                        code=a.code,
                        name=name,
                        description=desc,
                        # A procedure reachable only through research carries the same
                        # caveat the route does. With no route named, the jurisdiction and
                        # the procedure are all there is to judge it by.
                        is_research=not (
                            scope_is_live(jurisdiction, visa_cat, a)
                            if visa_cat is not None
                            else jurisdiction.is_live and a.is_live
                        ),
                    )
                )
            # As with the routes: a known destination offers what it has, or nothing.
            return result

    app_types = get_application_types()
    return [ApplicationTypeOut.model_validate(at) for at in app_types]


@router.get("/all", response_model=GeoDataOut)
async def get_all_geo_data(
    request: Request,
    session: SessionDep,
) -> GeoDataOut:
    """Get all geolocation data in one call (for frontend initialization)."""
    geo = await detect_country_from_ip(request)

    destinations = []
    if session:
        live_jurisdictions = (
            await session.scalars(
                select(Jurisdiction)
                .where(Jurisdiction.is_live.is_(True), Jurisdiction.is_enabled.is_(True))
                .order_by(Jurisdiction.name)
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
        visa_types=[VisaTypeOut.model_validate(vt) for vt in visa_types],
        application_types=[ApplicationTypeOut.model_validate(at) for at in app_types],
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
