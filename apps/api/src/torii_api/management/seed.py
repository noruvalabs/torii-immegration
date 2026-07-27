"""Seed the database with sample users, jurisdictions, visa categories, and actions.

Usage::

    uv run python -m torii_api.management.seed

Creates:
- 5 users (admin, ops, employer, 2 applicants)
- 3 jurisdictions (US, JP, DE)
- Visa categories per jurisdiction (JP: work, student, dependent; US: h1b, f1; DE: work)
- Case actions per jurisdiction (JP: renewal, new_application, change_of_status; same for US/DE)

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
    Jurisdiction,
    User,
    UserRole,
    VisaCategory,
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
            existing = await session.scalar(
                select(User).where(User.email == data["email"])
            )
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
                    continue
                vc = VisaCategory(
                    jurisdiction_id=jid,
                    code=data["code"],
                    name=data["name"],
                    is_live=data["is_live"],
                )
                session.add(vc)
                created_categories += 1

        created_actions = 0
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
                    continue
                ca = CaseAction(
                    jurisdiction_id=jid,
                    code=data["code"],
                    name=data["name"],
                    is_live=data["is_live"],
                )
                session.add(ca)
                created_actions += 1

        await session.commit()

    await engine.dispose()
    print(
        f"Seeded {created_users} users, {created_jurisdictions} jurisdictions, "
        f"{created_categories} visa categories, {created_actions} case actions"
    )


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
