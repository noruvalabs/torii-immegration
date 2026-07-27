"""Seed the database with sample users and jurisdictions.

Usage::

    uv run python -m torii_api.management.seed

Creates:
- 1 admin user (admin@example.com / admin-pass-123)
- 1 ops user (ops@example.com / ops-pass-123)
- 1 employer user (employer@example.com / employer-pass-123)
- 2 applicant users (applicant1@example.com, applicant2@example.com / applicant-pass-123)
- 3 sample jurisdictions (US, JP, DE)

Idempotent: skips records that already exist (by email / code).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from torii_api.auth.security import hash_password
from torii_api.config import get_settings
from torii_api.db.base import Base
from torii_api.db.engine import create_engine, create_session_factory, to_async_url
from torii_api.db.models import Jurisdiction, User, UserRole

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
        for data in SEED_JURISDICTIONS:
            existing = await session.scalar(
                select(Jurisdiction).where(Jurisdiction.code == data["code"])
            )
            if existing is not None:
                continue
            jurisdiction = Jurisdiction(
                code=data["code"],
                name=data["name"],
                is_live=data["is_live"],
            )
            session.add(jurisdiction)
            created_jurisdictions += 1

        await session.commit()

    await engine.dispose()
    print(f"Seeded {created_users} users and {created_jurisdictions} jurisdictions")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
