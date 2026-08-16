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

# Extra markets without full content packs (empty for now — only JP, US, UK live).
SEED_EXTRA_JURISDICTIONS: list[dict[str, Any]] = []

SEED_EXTRA_CATEGORIES = [
    {"code": "tourist", "name": "Tourist / Visitor", "is_live": True},
    {"code": "student", "name": "Student", "is_live": True},
    {"code": "work", "name": "Work", "is_live": True},
]

SEED_EXTRA_ACTIONS = [
    {"code": "new", "name": "New Visa", "is_live": True},
    {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    {"code": "new_application", "name": "New application", "is_live": True},
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
    jurisdiction_ids: dict[str, int],
) -> int:
    existing = await session.scalar(select(Jurisdiction).where(Jurisdiction.code == code))
    if existing is not None:
        existing.is_live = is_live
        existing.name = name
        jurisdiction_ids[code] = existing.id
        return 0
    jurisdiction = Jurisdiction(code=code, name=name, is_live=is_live)
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
        category_ids[(j_code, code)] = existing.id
        return 0
    vc = VisaCategory(
        jurisdiction_id=jid,
        code=code,
        name=name,
        is_live=is_live,
        research_enabled=research_enabled,
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
        action_ids[(j_code, code)] = existing.id
        return 0
    ca = CaseAction(
        jurisdiction_id=jid,
        code=code,
        name=name,
        is_live=is_live,
        research_enabled=research_enabled,
    )
    session.add(ca)
    await session.flush()
    action_ids[(j_code, code)] = ca.id
    return 1


async def seed() -> None:
    settings = get_settings()
    engine = create_engine(to_async_url(settings.database_url))
    session_factory = create_session_factory(engine)
    packs = load_all_packs()
    pack_jurisdictions = list_jurisdiction_metas()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        created_users = 0
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
                    action_ids=action_ids,
                )

        for data in SEED_EXTRA_JURISDICTIONS:
            created_jurisdictions += await _ensure_jurisdiction(
                session,
                code=data["code"],
                name=data["name"],
                is_live=bool(data["is_live"]),
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

        created_workflow_definitions = 0
        # Static YAML pack workflow definitions are disabled: all scopes are research-driven via live web search + LLM.

        await session.commit()

    await engine.dispose()
    print(
        f"Seeded {created_users} users, {created_jurisdictions} jurisdictions, "
        f"{created_categories} visa categories, {created_actions} case actions, "
        f"{created_workflow_definitions} applicant workflow definitions "
        f"from {len(packs)} content packs"
    )


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
