"""Seed the database with sample users and jurisdiction content packs.

Usage::

    uv run python -m torii_api.management.seed

Creates:
- 5 users (admin, ops, employer, 2 applicants)
- Jurisdictions / categories / actions from ``docs/jurisdictions/*/``
- Live intake + eligibility + documents + forms from content packs

Idempotent: skips records that already exist (by email / code).
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.security import hash_password
from torii_api.config import get_settings
from torii_api.db.base import Base
from torii_api.db.engine import create_engine, create_session_factory, to_async_url
from torii_api.db.models import (
    CaseAction,
    ConciergeProduct,
    DocumentRequirementSet,
    EligibilityRuleSet,
    FormTemplate,
    IntakeDefinition,
    Jurisdiction,
    User,
    UserRole,
    VisaCategory,
)
from torii_api.services.content_packs import (
    list_jurisdiction_metas,
    load_all_packs,
    workflow_rows_from_packs,
)
from torii_api.services.scope_discovery import SOURCE_PACK

SEED_USERS = [
    {
        "email": "admin@example.com",
        "password": "admin-pass-123",
        "role": UserRole.ADMIN,
        "email_verified": True,
    },
    {
        "email": "ops@example.com",
        "password": "ops-pass-123",
        "role": UserRole.OPS,
        "email_verified": True,
    },
    {
        "email": "employer@example.com",
        "password": "employer-pass-123",
        "role": UserRole.EMPLOYER,
        "email_verified": True,
    },
    {
        "email": "applicant1@example.com",
        "password": "applicant-pass-123",
        "role": UserRole.APPLICANT,
        "email_verified": True,
    },
    {
        "email": "applicant2@example.com",
        "password": "applicant-pass-123",
        "role": UserRole.APPLICANT,
        "email_verified": False,
    },
]

# Extra markets without full content packs.
SEED_EXTRA_JURISDICTIONS: list[dict[str, Any]] = [
    {"code": "SA", "name": "Saudi Arabia", "is_live": True, "submission_track": "digital"},
    {"code": "MY", "name": "Malaysia", "is_live": True, "submission_track": "digital"},
    {"code": "TR", "name": "Turkey", "is_live": True, "submission_track": "digital"},
    {"code": "VN", "name": "Vietnam", "is_live": True, "submission_track": "digital"},
    {"code": "EG", "name": "Egypt", "is_live": True, "submission_track": "digital"},
    {"code": "BH", "name": "Bahrain", "is_live": True, "submission_track": "digital"},
    {"code": "US", "name": "United States", "is_live": True, "submission_track": "consular"},
    {"code": "CA", "name": "Canada", "is_live": True, "submission_track": "hybrid"},
    {"code": "KR", "name": "South Korea", "is_live": True, "submission_track": "consular"},
    {"code": "FR", "name": "France", "is_live": True, "submission_track": "consular"},
    {"code": "DE", "name": "Germany", "is_live": True, "submission_track": "consular"},
    {"code": "ES", "name": "Spain", "is_live": True, "submission_track": "consular"},
]

SEED_EXTRA_CATEGORIES = [
    {"code": "tourist", "name": "Tourist / Visitor", "is_live": True},
    {"code": "student", "name": "Student", "is_live": True},
    {"code": "work", "name": "Work", "is_live": True},
]

SEED_EXTRA_ACTIONS = [
    {"code": "new", "name": "New Visa", "is_live": True},
    {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    {"code": "new_application", "name": "New application", "is_live": True},
    {"code": "change_of_status", "name": "Change of status", "is_live": True},
]

GENERIC_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "full_name",
        "prompt": "What is your full name?",
        "type": "string",
        "required": True,
    },
    {
        "key": "nationality",
        "prompt": "What is your nationality?",
        "type": "string",
        "required": True,
    },
    {
        "key": "passport_number",
        "prompt": "What is your passport number?",
        "type": "string",
        "required": True,
    },
    {
        "key": "passport_expiry",
        "prompt": "When does your passport expire?",
        "type": "string",
        "required": True,
    },
    {
        "key": "purpose_of_visit",
        "prompt": "What is the purpose of your visit?",
        "type": "string",
        "required": True,
    },
    {
        "key": "duration_of_stay",
        "prompt": "How long do you plan to stay?",
        "type": "string",
        "required": True,
    },
    {
        "key": "has_return_ticket",
        "prompt": "Do you have a return ticket?",
        "type": "boolean",
        "required": True,
    },
    {
        "key": "has_sufficient_funds",
        "prompt": "Do you have sufficient funds for your stay?",
        "type": "boolean",
        "required": True,
    },
]
GENERIC_RULES: list[dict[str, Any]] = [
    {
        "key": "passport_expiry",
        "operator": "not_empty",
        "value": None,
        "failure_status": "fail",
        "message": "You must have a valid passport with expiry date",
        "citation": {
            "authority": "Torii",
            "title": "Generic intake fallback",
            "url": "https://www.moj.go.jp/isa/",
        },
    },
    {
        "key": "has_sufficient_funds",
        "operator": "equals",
        "value": True,
        "failure_status": "fail",
        "message": "You must demonstrate sufficient funds",
        "citation": {
            "authority": "Torii",
            "title": "Generic intake fallback",
            "url": "https://www.moj.go.jp/isa/",
        },
    },
]
GENERIC_DOCUMENTS: list[dict[str, Any]] = [
    {
        "code": "passport",
        "name": "Valid Passport",
        "is_required": True,
        "how_to_obtain": "Valid passport from your home country",
        "why_required": "Primary identification",
        "citation": {
            "authority": "Torii",
            "title": "Generic intake fallback",
            "url": "https://www.moj.go.jp/isa/",
        },
    },
    {
        "code": "photo",
        "name": "Passport Photo",
        "is_required": True,
        "how_to_obtain": "Recent passport-style photograph",
        "why_required": "Required for application",
        "citation": {
            "authority": "Torii",
            "title": "Generic intake fallback",
            "url": "https://www.moj.go.jp/isa/",
        },
    },
    {
        "code": "proof_of_funds",
        "name": "Proof of Funds",
        "is_required": True,
        "how_to_obtain": "Bank statement or financial proof",
        "why_required": "Demonstrates financial capability",
        "citation": {
            "authority": "Torii",
            "title": "Generic intake fallback",
            "url": "https://www.moj.go.jp/isa/",
        },
    },
    {
        "code": "travel_itinerary",
        "name": "Travel Itinerary",
        "is_required": True,
        "how_to_obtain": "Flight booking and hotel reservations",
        "why_required": "Shows travel plans",
        "citation": {
            "authority": "Torii",
            "title": "Generic intake fallback",
            "url": "https://www.moj.go.jp/isa/",
        },
    },
]
GENERIC_FORM: dict[str, Any] = {
    "code": "generic_visa_application",
    "version": "1.0",
    "official_title": "Visa Application Form",
    "citation": {
        "authority": "Torii",
        "title": "Generic intake fallback",
        "url": "https://www.moj.go.jp/isa/",
    },
    "field_mappings": [
        {"form_field": "full_name", "answer_key": "full_name", "required": True},
        {"form_field": "nationality", "answer_key": "nationality", "required": True},
        {"form_field": "passport_number", "answer_key": "passport_number", "required": True},
        {"form_field": "purpose", "answer_key": "purpose_of_visit", "required": True},
        {"form_field": "duration", "answer_key": "duration_of_stay", "required": True},
    ],
}


async def _seed_workflow(
    session: AsyncSession,
    *,
    jurisdiction_id: int,
    visa_category_id: int,
    case_action_id: int,
    questions: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    form: dict[str, Any] | None = None,
    forms: list[dict[str, Any]] | None = None,
) -> int:
    created = 0
    existing_intake = await session.scalar(
        select(IntakeDefinition).where(
            IntakeDefinition.jurisdiction_id == jurisdiction_id,
            IntakeDefinition.visa_category_id == visa_category_id,
            IntakeDefinition.case_action_id == case_action_id,
        )
    )
    if existing_intake is None:
        session.add(
            IntakeDefinition(
                jurisdiction_id=jurisdiction_id,
                visa_category_id=visa_category_id,
                case_action_id=case_action_id,
                questions=questions,
                is_live=True,
            )
        )
        created += 1
    else:
        existing_intake.questions = questions
        existing_intake.is_live = True

    for model, values in (
        (EligibilityRuleSet, {"rules": rules}),
        (DocumentRequirementSet, {"items": documents}),
    ):
        existing = await session.scalar(
            select(model).where(
                model.jurisdiction_id == jurisdiction_id,
                model.visa_category_id == visa_category_id,
                model.case_action_id == case_action_id,
            )
        )
        if existing is None:
            session.add(
                model(
                    jurisdiction_id=jurisdiction_id,
                    visa_category_id=visa_category_id,
                    case_action_id=case_action_id,
                    is_live=True,
                    **values,
                )
            )
            created += 1
        else:
            for key, value in values.items():
                setattr(existing, key, value)
            existing.is_live = True

    all_forms: list[dict[str, Any]] = forms if forms is not None else ([form] if form else [])
    for f in all_forms:
        existing_form = await session.scalar(
            select(FormTemplate).where(
                FormTemplate.jurisdiction_id == jurisdiction_id,
                FormTemplate.visa_category_id == visa_category_id,
                FormTemplate.case_action_id == case_action_id,
                FormTemplate.code == f["code"],
            )
        )
        if existing_form is None:
            session.add(
                FormTemplate(
                    jurisdiction_id=jurisdiction_id,
                    visa_category_id=visa_category_id,
                    case_action_id=case_action_id,
                    is_live=True,
                    **f,
                )
            )
            created += 1
        else:
            for key, value in f.items():
                setattr(existing_form, key, value)
            existing_form.is_live = True

    return created


async def _ensure_jurisdiction(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    is_live: bool,
    submission_track: str = "consular",
    jurisdiction_ids: dict[str, int],
) -> int:
    existing = await session.scalar(select(Jurisdiction).where(Jurisdiction.code == code))
    if existing is not None:
        existing.is_live = is_live
        existing.name = name
        existing.submission_track = submission_track
        jurisdiction_ids[code] = existing.id
        return 0
    jurisdiction = Jurisdiction(
        code=code, name=name, is_live=is_live, submission_track=submission_track
    )
    session.add(jurisdiction)
    await session.flush()
    jurisdiction_ids[code] = jurisdiction.id
    return 1


async def _ensure_category(
    session: AsyncSession,
    *,
    jid: int,
    j_code: str,
    code: str,
    name: str,
    is_live: bool,
    research_enabled: bool = False,
    description: str = "",
    submission_track: str | None = None,
    category_ids: dict[tuple[str, str], int],
) -> int:
    existing = await session.scalar(
        select(VisaCategory).where(
            VisaCategory.jurisdiction_id == jid,
            VisaCategory.code == code,
        )
    )
    if existing is not None:
        existing.is_live = is_live
        existing.name = name
        existing.research_enabled = research_enabled
        existing.source = SOURCE_PACK
        if description:
            existing.description = description
        if submission_track is not None:
            existing.submission_track = submission_track
        # ``is_enabled`` is untouched on purpose: it is the admin's switch, and a reseed
        # putting a route an admin turned off back on is the failure it exists to avoid.
        category_ids[(j_code, code)] = existing.id
        return 0
    vc = VisaCategory(
        jurisdiction_id=jid,
        code=code,
        name=name,
        is_live=is_live,
        research_enabled=research_enabled,
        description=description,
        source=SOURCE_PACK,
        submission_track=submission_track,
    )
    session.add(vc)
    await session.flush()
    category_ids[(j_code, code)] = vc.id
    return 1


async def _ensure_action(
    session: AsyncSession,
    *,
    jid: int,
    j_code: str,
    code: str,
    name: str,
    is_live: bool,
    research_enabled: bool = False,
    description: str = "",
    action_ids: dict[tuple[str, str], int],
) -> int:
    existing = await session.scalar(
        select(CaseAction).where(
            CaseAction.jurisdiction_id == jid,
            CaseAction.code == code,
        )
    )
    if existing is not None:
        existing.is_live = is_live
        existing.name = name
        existing.research_enabled = research_enabled
        existing.source = SOURCE_PACK
        if description:
            existing.description = description
        # See ``_ensure_category``: the admin switch is not the pack's to set.
        action_ids[(j_code, code)] = existing.id
        return 0
    ca = CaseAction(
        jurisdiction_id=jid,
        code=code,
        name=name,
        is_live=is_live,
        research_enabled=research_enabled,
        description=description,
        source=SOURCE_PACK,
    )
    session.add(ca)
    await session.flush()
    action_ids[(j_code, code)] = ca.id
    return 1


CONCIERGE_PRODUCTS = [
    {
        "code": "dummy_flight",
        "name": "Dummy Flight Reservation",
        "description": "A verifiable flight reservation PDF valid for 14 days — accepted by all major consulates. No actual ticket purchase needed.",
        "product_type": "dummy_flight",
        "price_cents": 1200,
        "currency": "USD",
        "checklist_code_pattern": "flight,itinerary,booking,ticket,air_ticket,flight_ticket,travel_itinerary,flight_reservation,flight_booking",
        "is_active": True,
    },
    {
        "code": "travel_insurance",
        "name": "Travel Insurance Certificate",
        "description": "Travel medical insurance certificate covering your trip dates with minimum required coverage. Instant PDF delivery.",
        "product_type": "travel_insurance",
        "price_cents": 1500,
        "currency": "USD",
        "checklist_code_pattern": "insurance,travel_insurance,medical_insurance,health_insurance",
        "is_active": True,
    },
    {
        "code": "doctor_referral",
        "name": "Doctor Referral Letter",
        "description": "AI-generated medical referral letter template customised to your visa requirements. Review and get signed by your physician.",
        "product_type": "doctor_referral",
        "price_cents": 1900,
        "currency": "USD",
        "checklist_code_pattern": "referral,doctor,medical_referral,doctor_letter,medical_letter",
        "is_active": True,
    },
    {
        "code": "hotel_reservation",
        "name": "Hotel Confirmation Letter",
        "description": "Free hotel confirmation letter via our Booking.com partner. Shows proof of accommodation for your visa application.",
        "product_type": "hotel_reservation",
        "price_cents": 0,
        "currency": "USD",
        "checklist_code_pattern": "hotel,accommodation,hotel_booking,hotel_reservation,lodging,accommodation_proof",
        "is_active": True,
    },
    {
        "code": "invitation_letter",
        "name": "Invitation Letter",
        "description": "AI-generated invitation letter from your host, formatted to meet consulate requirements. Editable before download.",
        "product_type": "invitation_letter",
        "price_cents": 1400,
        "currency": "USD",
        "checklist_code_pattern": "invitation,host_letter,invitation_letter,sponsor_letter",
        "is_active": True,
    },
]


async def _seed_concierge_products(session: AsyncSession) -> int:
    created = 0
    for p in CONCIERGE_PRODUCTS:
        existing = await session.scalar(
            select(ConciergeProduct).where(ConciergeProduct.code == p["code"])
        )
        if existing is None:
            session.add(ConciergeProduct(**p))
            created += 1
        else:
            for k, v in p.items():
                setattr(existing, k, v)
    return created


async def seed(
    session_factory: Any | None = None,
    include_demo_users: bool | None = None,
) -> None:
    """Load the content packs into the system of record.

    ``session_factory`` is for callers that already have a database — the tests, which
    run against a throwaway one. Left out, this opens its own from settings as the CLI
    entry point needs.
    """
    settings = get_settings()
    if include_demo_users is None:
        include_demo_users = settings.seed_demo_users
    engine = create_engine(to_async_url(settings.database_url)) if session_factory is None else None
    owns_engine = engine is not None
    if session_factory is None:
        assert engine is not None
        session_factory = create_session_factory(engine)
    packs = load_all_packs()
    pack_jurisdictions = list_jurisdiction_metas()

    # SQLite only, and deliberately so. `create_all` builds tables straight from the models,
    # which is exactly what the zero-setup local path wants (no migration step to run first)
    # and exactly what a real database must never have: it bypasses Alembic, so a table the
    # models know about but no migration creates would be conjured into existence here with
    # no alembic_version row to say it happened. The schema then differs from a
    # freshly-migrated one, and the migration that eventually adds that table fails on this
    # database while passing everywhere else.
    #
    # On Postgres, Alembic is the only thing allowed to change the schema — the API already
    # runs it at startup via `migrate_on_startup`, before this function is ever called.
    if engine is not None and settings.is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        created_users = 0
        if include_demo_users:
            for data in SEED_USERS:
                username = data["email"].split("@")[0]
                existing = await session.scalar(
                    select(User).where((User.email == data["email"]) | (User.username == username))
                )
                if existing is not None:
                    continue
                user = User(
                    email=data["email"],
                    username=username,
                    password_hash=hash_password(data["password"]),
                    role=data["role"],
                    is_active=True,
                    email_verified=data["email_verified"],
                )
                session.add(user)
                created_users += 1

        created_jurisdictions = 0
        created_categories = 0
        created_actions = 0
        jurisdiction_ids: dict[str, int] = {}
        category_ids: dict[tuple[str, str], int] = {}
        action_ids: dict[tuple[str, str], int] = {}

        for meta in pack_jurisdictions:
            created_jurisdictions += await _ensure_jurisdiction(
                session,
                code=meta.code.upper(),
                name=meta.name,
                is_live=meta.is_live,
                submission_track=getattr(meta, "submission_track", "consular"),
                jurisdiction_ids=jurisdiction_ids,
            )
            jid = jurisdiction_ids[meta.code.upper()]
            for cat in meta.categories:
                created_categories += await _ensure_category(
                    session,
                    jid=jid,
                    j_code=meta.code.upper(),
                    code=str(cat["code"]).lower(),
                    name=str(cat["name"]),
                    is_live=bool(cat.get("is_live", True)),
                    research_enabled=True,
                    description=str(cat.get("description") or ""),
                    submission_track=cat.get("submission_track"),
                    category_ids=category_ids,
                )
            for action in meta.actions:
                created_actions += await _ensure_action(
                    session,
                    jid=jid,
                    j_code=meta.code.upper(),
                    code=str(action["code"]).lower(),
                    name=str(action["name"]),
                    is_live=bool(action.get("is_live", True)),
                    research_enabled=True,
                    description=str(action.get("description") or ""),
                    action_ids=action_ids,
                )

        for data in SEED_EXTRA_JURISDICTIONS:
            created_jurisdictions += await _ensure_jurisdiction(
                session,
                code=data["code"],
                name=data["name"],
                is_live=bool(data["is_live"]),
                submission_track=data.get("submission_track", "consular"),
                jurisdiction_ids=jurisdiction_ids,
            )
            jid = jurisdiction_ids[data["code"]]
            for cat in SEED_EXTRA_CATEGORIES:
                created_categories += await _ensure_category(
                    session,
                    jid=jid,
                    j_code=data["code"],
                    code=cat["code"],
                    name=cat["name"],
                    is_live=bool(cat["is_live"]),
                    research_enabled=True,
                    category_ids=category_ids,
                )
            for action in SEED_EXTRA_ACTIONS:
                created_actions += await _ensure_action(
                    session,
                    jid=jid,
                    j_code=data["code"],
                    code=action["code"],
                    name=action["name"],
                    is_live=bool(action["is_live"]),
                    research_enabled=True,
                    action_ids=action_ids,
                )
            # Seed generic workflows for extra jurisdictions
            for cat in SEED_EXTRA_CATEGORIES:
                cid = category_ids.get((data["code"], cat["code"]))
                for action in SEED_EXTRA_ACTIONS:
                    aid = action_ids.get((data["code"], action["code"]))
                    if jid and cid and aid:
                        await _seed_workflow(
                            session,
                            jurisdiction_id=jid,
                            visa_category_id=cid,
                            case_action_id=aid,
                            questions=GENERIC_QUESTIONS,
                            rules=GENERIC_RULES,
                            documents=GENERIC_DOCUMENTS,
                        )

        created_workflow_definitions = 0
        workflow_rows = workflow_rows_from_packs(packs)
        for row in workflow_rows:
            j_code = row["jurisdiction"]
            cat_code = row["visa_category"]
            act_code = row["action"]
            jid = jurisdiction_ids.get(j_code)
            cid = category_ids.get((j_code, cat_code))

            # Match action and aliases (e.g. "new" vs "new_application")
            target_actions = [act_code]
            if act_code == "new_application":
                target_actions.append("new")
            elif act_code == "new":
                target_actions.append("new_application")

            for target_act in target_actions:
                aid = action_ids.get((j_code, target_act))
                if jid and cid and aid:
                    created_workflow_definitions += await _seed_workflow(
                        session,
                        jurisdiction_id=jid,
                        visa_category_id=cid,
                        case_action_id=aid,
                        questions=row["questions"],
                        rules=row["rules"],
                        documents=row["documents"],
                        form=row.get("form"),
                        forms=row.get("forms"),
                    )

        created_concierge = await _seed_concierge_products(session)
        await session.commit()

    if owns_engine and engine is not None:
        await engine.dispose()
    print(
        f"Seeded {created_users} users, {created_jurisdictions} jurisdictions, "
        f"{created_categories} visa categories, {created_actions} case actions, "
        f"{created_workflow_definitions} applicant workflow definitions, "
        f"{created_concierge} concierge products "
        f"from {len(packs)} content packs"
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Seed database with jurisdiction content packs.")
    parser.add_argument(
        "--include-demo-users",
        action="store_true",
        default=None,
        help="Seed sample development demo users (admin@example.com, etc.).",
    )
    parser.add_argument(
        "--no-demo-users",
        action="store_false",
        dest="include_demo_users",
        help="Skip demo users; only seed jurisdiction packs, workflows, and form templates.",
    )
    args = parser.parse_args()
    asyncio.run(seed(include_demo_users=args.include_demo_users))


if __name__ == "__main__":
    main()
