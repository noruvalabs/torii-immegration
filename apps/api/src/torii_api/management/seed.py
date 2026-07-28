"""Seed the database with sample users, jurisdictions, visa categories, and actions.

Usage::

    uv run python -m torii_api.management.seed

Creates:
- 5 users (admin, ops, employer, 2 applicants)
- 3 jurisdictions (US, JP, DE)
- Visa categories per jurisdiction (JP: work, student, dependent; US: h1b, f1; DE: work)
- Case actions per jurisdiction (JP: renewal, new_application, change_of_status; same for US/DE)
- Live intake definition for JP / work / renewal (US-02)

Idempotent: skips records that already exist (by email / code).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

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
from torii_api.services.checklist import JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS
from torii_api.services.eligibility import JP_WORK_RENEWAL_ELIGIBILITY_RULES
from torii_api.services.forms import JP_WORK_RENEWAL_FORM_TEMPLATE
from torii_api.services.intake import JP_WORK_RENEWAL_QUESTIONS

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

SEED_JURISDICTIONS = [
    {"code": "US", "name": "United States", "is_live": True},
    {"code": "JP", "name": "Japan", "is_live": True},
    {"code": "DE", "name": "Germany", "is_live": False},
]

SEED_VISA_CATEGORIES = {
    "JP": [
        {"code": "work", "name": "Work Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "dependent", "name": "Dependent Visa", "is_live": False},
    ],
    "US": [
        {"code": "h1b", "name": "H-1B Specialty Worker", "is_live": True},
        {"code": "f1", "name": "F-1 Student", "is_live": False},
    ],
    "DE": [
        {"code": "work", "name": "Work Visa", "is_live": False},
    ],
}

SEED_CASE_ACTIONS = {
    "JP": [
        {"code": "renewal", "name": "Renewal", "is_live": True},
        {"code": "new_application", "name": "New Application", "is_live": True},
        {"code": "change_of_status", "name": "Change of Status", "is_live": False},
    ],
    "US": [
        {"code": "renewal", "name": "Renewal", "is_live": True},
        {"code": "new_application", "name": "New Application", "is_live": True},
    ],
    "DE": [
        {"code": "renewal", "name": "Renewal", "is_live": False},
    ],
}


async def seed() -> None:
    settings = get_settings()
    engine = create_engine(to_async_url(settings.database_url))
    session_factory = create_session_factory(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        created_users = 0
        for data in SEED_USERS:
            existing = await session.scalar(select(User).where(User.email == data["email"]))
            if existing is not None:
                continue
            user = User(
                email=data["email"],
                username=data["email"].split("@")[0],
                password_hash=hash_password(data["password"]),
                role=data["role"],
                is_active=True,
                email_verified=data["email_verified"],
            )
            session.add(user)
            created_users += 1

        created_jurisdictions = 0
        jurisdiction_ids: dict[str, int] = {}
        for data in SEED_JURISDICTIONS:
            existing = await session.scalar(
                select(Jurisdiction).where(Jurisdiction.code == data["code"])
            )
            if existing is not None:
                jurisdiction_ids[data["code"]] = existing.id
                continue
            jurisdiction = Jurisdiction(
                code=data["code"],
                name=data["name"],
                is_live=data["is_live"],
            )
            session.add(jurisdiction)
            await session.flush()
            jurisdiction_ids[data["code"]] = jurisdiction.id
            created_jurisdictions += 1

        created_categories = 0
        category_ids: dict[tuple[str, str], int] = {}
        for code, categories in SEED_VISA_CATEGORIES.items():
            jid = jurisdiction_ids.get(code)
            if jid is None:
                continue
            for data in categories:
                existing = await session.scalar(
                    select(VisaCategory).where(
                        VisaCategory.jurisdiction_id == jid,
                        VisaCategory.code == data["code"],
                    )
                )
                if existing is not None:
                    category_ids[(code, data["code"])] = existing.id
                    continue
                vc = VisaCategory(
                    jurisdiction_id=jid,
                    code=data["code"],
                    name=data["name"],
                    is_live=data["is_live"],
                )
                session.add(vc)
                await session.flush()
                category_ids[(code, data["code"])] = vc.id
                created_categories += 1

        created_actions = 0
        action_ids: dict[tuple[str, str], int] = {}
        for code, actions in SEED_CASE_ACTIONS.items():
            jid = jurisdiction_ids.get(code)
            if jid is None:
                continue
            for data in actions:
                existing = await session.scalar(
                    select(CaseAction).where(
                        CaseAction.jurisdiction_id == jid,
                        CaseAction.code == data["code"],
                    )
                )
                if existing is not None:
                    action_ids[(code, data["code"])] = existing.id
                    continue
                ca = CaseAction(
                    jurisdiction_id=jid,
                    code=data["code"],
                    name=data["name"],
                    is_live=data["is_live"],
                )
                session.add(ca)
                await session.flush()
                action_ids[(code, data["code"])] = ca.id
                created_actions += 1

        created_intake = 0
        created_workflow_definitions = 0
        jp_id = jurisdiction_ids.get("JP")
        work_id = category_ids.get(("JP", "work"))
        renewal_id = action_ids.get(("JP", "renewal"))
        if jp_id is not None and work_id is not None and renewal_id is not None:
            existing_intake = await session.scalar(
                select(IntakeDefinition).where(
                    IntakeDefinition.jurisdiction_id == jp_id,
                    IntakeDefinition.visa_category_id == work_id,
                    IntakeDefinition.case_action_id == renewal_id,
                )
            )
            if existing_intake is None:
                session.add(
                    IntakeDefinition(
                        jurisdiction_id=jp_id,
                        visa_category_id=work_id,
                        case_action_id=renewal_id,
                        questions=JP_WORK_RENEWAL_QUESTIONS,
                        is_live=True,
                    )
                )
                created_intake = 1

            workflow_definitions = (
                (
                    EligibilityRuleSet,
                    {"rules": JP_WORK_RENEWAL_ELIGIBILITY_RULES},
                ),
                (
                    DocumentRequirementSet,
                    {"items": JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS},
                ),
            )
            for model, values in workflow_definitions:
                existing = await session.scalar(
                    select(model).where(
                        model.jurisdiction_id == jp_id,
                        model.visa_category_id == work_id,
                        model.case_action_id == renewal_id,
                    )
                )
                if existing is None:
                    session.add(
                        model(
                            jurisdiction_id=jp_id,
                            visa_category_id=work_id,
                            case_action_id=renewal_id,
                            is_live=True,
                            **values,
                        )
                    )
                    created_workflow_definitions += 1

            existing_form = await session.scalar(
                select(FormTemplate).where(
                    FormTemplate.jurisdiction_id == jp_id,
                    FormTemplate.visa_category_id == work_id,
                    FormTemplate.case_action_id == renewal_id,
                    FormTemplate.code == JP_WORK_RENEWAL_FORM_TEMPLATE["code"],
                )
            )
            if existing_form is None:
                session.add(
                    FormTemplate(
                        jurisdiction_id=jp_id,
                        visa_category_id=work_id,
                        case_action_id=renewal_id,
                        is_live=True,
                        **JP_WORK_RENEWAL_FORM_TEMPLATE,
                    )
                )
                created_workflow_definitions += 1

        await session.commit()

    await engine.dispose()
    print(
        f"Seeded {created_users} users, {created_jurisdictions} jurisdictions, "
        f"{created_categories} visa categories, {created_actions} case actions, "
        f"{created_intake} intake definitions, "
        f"{created_workflow_definitions} applicant workflow definitions"
    )


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
