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
    JP_TOURIST_NEW_APPLICATION_DOCUMENT_REQUIREMENTS,
    JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS,
    US_H1B_DOCUMENT_REQUIREMENTS,
)
from torii_api.services.eligibility import (
    JP_STUDENT_NEW_APPLICATION_ELIGIBILITY_RULES,
    JP_TOURIST_NEW_APPLICATION_ELIGIBILITY_RULES,
    JP_WORK_RENEWAL_ELIGIBILITY_RULES,
    US_H1B_ELIGIBILITY_RULES,
)
from torii_api.services.forms import (
    JP_STUDENT_NEW_APPLICATION_FORM_TEMPLATE,
    JP_TOURIST_NEW_APPLICATION_FORM_TEMPLATE,
    JP_WORK_RENEWAL_FORM_TEMPLATE,
    US_H1B_FORM_TEMPLATE,
)
from torii_api.services.intake import (
    JP_STUDENT_NEW_APPLICATION_QUESTIONS,
    JP_TOURIST_NEW_APPLICATION_QUESTIONS,
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
    {"code": "GB", "name": "United Kingdom", "is_live": True},
    {"code": "CA", "name": "Canada", "is_live": True},
    {"code": "AU", "name": "Australia", "is_live": True},
    {"code": "DE", "name": "Germany", "is_live": True},
    {"code": "FR", "name": "France", "is_live": True},
    {"code": "SG", "name": "Singapore", "is_live": True},
    {"code": "KR", "name": "South Korea", "is_live": True},
    {"code": "NZ", "name": "New Zealand", "is_live": True},
    {"code": "IE", "name": "Ireland", "is_live": True},
    {"code": "NL", "name": "Netherlands", "is_live": True},
    {"code": "SE", "name": "Sweden", "is_live": True},
    {"code": "NO", "name": "Norway", "is_live": True},
    {"code": "CH", "name": "Switzerland", "is_live": True},
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
            "is_live": True,
        },
    ],
    "US": [
        {"code": "tourist", "name": "Tourist / Visitor Visa (B1/B2)", "is_live": True},
        {"code": "student", "name": "Student Visa (F-1)", "is_live": True},
        {"code": "work", "name": "Work Visa (H-1B)", "is_live": True},
    ],
    "GB": [
        {"code": "tourist", "name": "Standard Visitor Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "work", "name": "Skilled Worker Visa", "is_live": True},
    ],
    "CA": [
        {"code": "tourist", "name": "Visitor Visa (TRV)", "is_live": True},
        {"code": "student", "name": "Study Permit", "is_live": True},
        {"code": "work", "name": "Work Permit", "is_live": True},
    ],
    "AU": [
        {"code": "tourist", "name": "Visitor Visa (Subclass 600)", "is_live": True},
        {"code": "student", "name": "Student Visa (Subclass 500)", "is_live": True},
        {"code": "work", "name": "Skilled Worker Visa (Subclass 482)", "is_live": True},
    ],
    "DE": [
        {"code": "tourist", "name": "Schengen Tourist Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "work", "name": "Work Visa", "is_live": True},
    ],
    "FR": [
        {"code": "tourist", "name": "Schengen Tourist Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "work", "name": "Work Visa", "is_live": True},
    ],
    "SG": [
        {"code": "tourist", "name": "Tourist Visa", "is_live": True},
        {"code": "student", "name": "Student Pass", "is_live": True},
        {"code": "work", "name": "Employment Pass", "is_live": True},
    ],
    "KR": [
        {"code": "tourist", "name": "Tourist Visa (C-3)", "is_live": True},
        {"code": "student", "name": "Student Visa (D-2)", "is_live": True},
        {"code": "work", "name": "Work Visa (E-7)", "is_live": True},
    ],
    "NZ": [
        {"code": "tourist", "name": "Visitor Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "work", "name": "Essential Skills Work Visa", "is_live": True},
    ],
    "IE": [
        {"code": "tourist", "name": "Tourist Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "work", "name": "Critical Skills Permit", "is_live": True},
    ],
    "NL": [
        {"code": "tourist", "name": "Schengen Tourist Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "work", "name": "Work Permit", "is_live": True},
    ],
    "SE": [
        {"code": "tourist", "name": "Schengen Tourist Visa", "is_live": True},
        {"code": "student", "name": "Student Residence Permit", "is_live": True},
        {"code": "work", "name": "Work Permit", "is_live": True},
    ],
    "NO": [
        {"code": "tourist", "name": "Schengen Tourist Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "work", "name": "Work Permit", "is_live": True},
    ],
    "CH": [
        {"code": "tourist", "name": "Schengen Tourist Visa", "is_live": True},
        {"code": "student", "name": "Student Visa", "is_live": True},
        {"code": "work", "name": "Work Permit", "is_live": True},
    ],
}

SEED_CASE_ACTIONS = {
    "JP": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "US": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "GB": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "CA": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "AU": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "DE": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "FR": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "SG": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "KR": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "NZ": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "IE": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "NL": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "SE": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "NO": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
    ],
    "CH": [
        {"code": "new", "name": "New Visa", "is_live": True},
        {"code": "renewal", "name": "Renewal / Extension", "is_live": True},
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
    {
        "jurisdiction": "JP",
        "visa_category": "tourist",
        "action": "new_application",
        "questions": JP_TOURIST_NEW_APPLICATION_QUESTIONS,
        "rules": JP_TOURIST_NEW_APPLICATION_ELIGIBILITY_RULES,
        "documents": JP_TOURIST_NEW_APPLICATION_DOCUMENT_REQUIREMENTS,
        "form": JP_TOURIST_NEW_APPLICATION_FORM_TEMPLATE,
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

        # Auto-create generic workflows for ALL live combinations without one
        GENERIC_QUESTIONS = [
            {"key": "full_name", "prompt": "What is your full name?", "type": "string", "required": True},
            {"key": "nationality", "prompt": "What is your nationality?", "type": "string", "required": True},
            {"key": "passport_number", "prompt": "What is your passport number?", "type": "string", "required": True},
            {"key": "passport_expiry", "prompt": "When does your passport expire?", "type": "string", "required": True},
            {"key": "purpose_of_visit", "prompt": "What is the purpose of your visit?", "type": "string", "required": True},
            {"key": "duration_of_stay", "prompt": "How long do you plan to stay?", "type": "string", "required": True},
            {"key": "has_return_ticket", "prompt": "Do you have a return ticket?", "type": "boolean", "required": True},
            {"key": "has_sufficient_funds", "prompt": "Do you have sufficient funds for your stay?", "type": "boolean", "required": True},
        ]
        GENERIC_RULES = [
            {"key": "passport_expiry", "operator": "not_empty", "value": None,
             "failure_status": "fail", "message": "You must have a valid passport with expiry date"},
            {"key": "has_sufficient_funds", "operator": "equals", "value": True,
             "failure_status": "fail", "message": "You must demonstrate sufficient funds"},
        ]
        GENERIC_DOCUMENTS = [
            {"code": "passport", "name": "Valid Passport", "is_required": True,
             "how_to_obtain": "Valid passport from your home country", "why_required": "Primary identification",
             "citation": {"source": "generic"}},
            {"code": "photo", "name": "Passport Photo", "is_required": True,
             "how_to_obtain": "Recent passport-style photograph", "why_required": "Required for application",
             "citation": {"source": "generic"}},
            {"code": "proof_of_funds", "name": "Proof of Funds", "is_required": True,
             "how_to_obtain": "Bank statement or financial proof", "why_required": "Demonstrates financial capability",
             "citation": {"source": "generic"}},
            {"code": "travel_itinerary", "name": "Travel Itinerary", "is_required": True,
             "how_to_obtain": "Flight booking and hotel reservations", "why_required": "Shows travel plans",
             "citation": {"source": "generic"}},
        ]
        GENERIC_FORM = {
            "code": "generic_visa_application",
            "version": "1.0",
            "official_title": "Visa Application Form",
            "citation": {"source": "generic"},
            "field_mappings": [
                {"form_field": "full_name", "answer_key": "full_name", "required": True},
                {"form_field": "nationality", "answer_key": "nationality", "required": True},
                {"form_field": "passport_number", "answer_key": "passport_number", "required": True},
                {"form_field": "purpose", "answer_key": "purpose_of_visit", "required": True},
                {"form_field": "duration", "answer_key": "duration_of_stay", "required": True},
            ],
        }

        for (j_code, v_code), vid in category_ids.items():
            for (a_j_code, a_code), aid in action_ids.items():
                if j_code != a_j_code:
                    continue
                jid = jurisdiction_ids.get(j_code)
                if jid is None:
                    continue
                # Skip if workflow already seeded
                existing = await session.scalar(
                    select(IntakeDefinition).where(
                        IntakeDefinition.jurisdiction_id == jid,
                        IntakeDefinition.visa_category_id == vid,
                        IntakeDefinition.case_action_id == aid,
                    )
                )
                if existing is not None:
                    continue
                created_workflow_definitions += await _seed_workflow(
                    session,
                    jurisdiction_id=jid,
                    visa_category_id=vid,
                    case_action_id=aid,
                    questions=GENERIC_QUESTIONS,
                    rules=GENERIC_RULES,
                    documents=GENERIC_DOCUMENTS,
                    form=GENERIC_FORM,
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
