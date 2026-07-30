"""Seed the database with sample users, jurisdictions, visa categories, and actions.

Usage::

    uv run python -m torii_api.management.seed

Creates:
- 5 users (admin, ops, employer, 2 applicants)
- 3 jurisdictions (US, JP, DE)
- Visa categories / actions with live flags only for fully defined workflows
- Live intake + eligibility + documents + forms for:
  - JP / work / renewal
  - US / h1b / renewal
  - US / h1b / new_application

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
from torii_api.services.checklist import (
    JP_STUDENT_NEW_APPLICATION_DOCUMENT_REQUIREMENTS,
    JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS,
    US_H1B_DOCUMENT_REQUIREMENTS,
)
from torii_api.services.eligibility import (
    JP_STUDENT_NEW_APPLICATION_ELIGIBILITY_RULES,
    JP_WORK_RENEWAL_ELIGIBILITY_RULES,
    US_H1B_ELIGIBILITY_RULES,
)
from torii_api.services.forms import (
    JP_STUDENT_NEW_APPLICATION_FORM_TEMPLATE,
    JP_WORK_RENEWAL_FORM_TEMPLATE,
    US_H1B_FORM_TEMPLATE,
)
from torii_api.services.intake import (
    JP_STUDENT_NEW_APPLICATION_QUESTIONS,
    JP_WORK_RENEWAL_QUESTIONS,
    US_H1B_QUESTIONS,
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

SEED_JURISDICTIONS = [
    {"code": "US", "name": "United States", "is_live": True},
    {"code": "JP", "name": "Japan", "is_live": True},
    {"code": "GB", "name": "United Kingdom", "is_live": False},
    {"code": "CA", "name": "Canada", "is_live": False},
    {"code": "AU", "name": "Australia", "is_live": False},
    {"code": "DE", "name": "Germany", "is_live": False},
    {"code": "FR", "name": "France", "is_live": False},
    {"code": "SG", "name": "Singapore", "is_live": False},
    {"code": "KR", "name": "South Korea", "is_live": False},
    {"code": "AE", "name": "United Arab Emirates", "is_live": False},
    {"code": "NZ", "name": "New Zealand", "is_live": False},
    {"code": "NL", "name": "Netherlands", "is_live": False},
    {"code": "IT", "name": "Italy", "is_live": False},
    {"code": "ES", "name": "Spain", "is_live": False},
    {"code": "CH", "name": "Switzerland", "is_live": False},
    {"code": "IE", "name": "Ireland", "is_live": False},
    {"code": "TH", "name": "Thailand", "is_live": False},
    {"code": "MY", "name": "Malaysia", "is_live": False},
    {"code": "IN", "name": "India", "is_live": False},
    {"code": "CN", "name": "China", "is_live": False},
]

# Live only when a full workflow is seeded below (US-01.3).
SEED_VISA_CATEGORIES = {
    "JP": [
        {
            "code": "student",
            "name": "Student Visa - Study at a university or language school",
            "is_live": True,
        },
        {
            "code": "work",
            "name": "Work Visa - Employment with a Japanese company",
            "is_live": True,
        },
        {
            "code": "tourist",
            "name": "Tourist Visa - Short-term travel (up to 90 days in many cases)",
            "is_live": False,
        },
        {
            "code": "business",
            "name": "Business Visa - Meetings, conferences, business visits",
            "is_live": False,
        },
        {
            "code": "dependent",
            "name": "Dependent Visa - Join a family member living in Japan",
            "is_live": False,
        },
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

# (jurisdiction, visa_category, action) -> workflow payload
WORKFLOW_SEEDS: list[dict[str, Any]] = [
    {
        "jurisdiction": "JP",
        "visa_category": "work",
        "action": "renewal",
        "questions": JP_WORK_RENEWAL_QUESTIONS,
        "rules": JP_WORK_RENEWAL_ELIGIBILITY_RULES,
        "documents": JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS,
        "form": JP_WORK_RENEWAL_FORM_TEMPLATE,
    },
    {
        "jurisdiction": "US",
        "visa_category": "h1b",
        "action": "renewal",
        "questions": US_H1B_QUESTIONS,
        "rules": US_H1B_ELIGIBILITY_RULES,
        "documents": US_H1B_DOCUMENT_REQUIREMENTS,
        "form": US_H1B_FORM_TEMPLATE,
    },
    {
        "jurisdiction": "US",
        "visa_category": "h1b",
        "action": "new_application",
        "questions": US_H1B_QUESTIONS,
        "rules": US_H1B_ELIGIBILITY_RULES,
        "documents": US_H1B_DOCUMENT_REQUIREMENTS,
        "form": US_H1B_FORM_TEMPLATE,
    },
    {
        "jurisdiction": "JP",
        "visa_category": "student",
        "action": "new_application",
        "questions": JP_STUDENT_NEW_APPLICATION_QUESTIONS,
        "rules": JP_STUDENT_NEW_APPLICATION_ELIGIBILITY_RULES,
        "documents": JP_STUDENT_NEW_APPLICATION_DOCUMENT_REQUIREMENTS,
        "form": JP_STUDENT_NEW_APPLICATION_FORM_TEMPLATE,
    },
]


async def _seed_workflow(
    session: AsyncSession,
    *,
    jurisdiction_id: int,
    visa_category_id: int,
    case_action_id: int,
    questions: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    form: dict[str, Any],
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

    existing_form = await session.scalar(
        select(FormTemplate).where(
            FormTemplate.jurisdiction_id == jurisdiction_id,
            FormTemplate.visa_category_id == visa_category_id,
            FormTemplate.case_action_id == case_action_id,
            FormTemplate.code == form["code"],
        )
    )
    if existing_form is None:
        session.add(
            FormTemplate(
                jurisdiction_id=jurisdiction_id,
                visa_category_id=visa_category_id,
                case_action_id=case_action_id,
                is_live=True,
                **form,
            )
        )
        created += 1
    else:
        for key, value in form.items():
            setattr(existing_form, key, value)
        existing_form.is_live = True

    return created


async def seed() -> None:
    settings = get_settings()
    engine = create_engine(to_async_url(settings.database_url))
    session_factory = create_session_factory(engine)

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
        jurisdiction_ids: dict[str, int] = {}
        for data in SEED_JURISDICTIONS:
            existing = await session.scalar(
                select(Jurisdiction).where(Jurisdiction.code == data["code"])
            )
            if existing is not None:
                existing.is_live = data["is_live"]
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
                    existing.is_live = data["is_live"]
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
                    existing.is_live = data["is_live"]
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

        created_workflow_definitions = 0
        for workflow in WORKFLOW_SEEDS:
            jid = jurisdiction_ids.get(workflow["jurisdiction"])
            vid = category_ids.get((workflow["jurisdiction"], workflow["visa_category"]))
            aid = action_ids.get((workflow["jurisdiction"], workflow["action"]))
            if jid is None or vid is None or aid is None:
                continue
            created_workflow_definitions += await _seed_workflow(
                session,
                jurisdiction_id=jid,
                visa_category_id=vid,
                case_action_id=aid,
                questions=workflow["questions"],
                rules=workflow["rules"],
                documents=workflow["documents"],
                form=workflow["form"],
            )

        await session.commit()

    await engine.dispose()
    print(
        f"Seeded {created_users} users, {created_jurisdictions} jurisdictions, "
        f"{created_categories} visa categories, {created_actions} case actions, "
        f"{created_workflow_definitions} applicant workflow definitions"
    )


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
