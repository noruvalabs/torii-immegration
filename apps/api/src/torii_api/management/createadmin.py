"""Create an admin user — Django-style ``createsuperuser`` for Torii.

Usage::

    uv run torii-createadmin --email admin@example.com

The command prompts for a password (hidden input) and inserts a user with
``role=admin`` into the database.  It respects ``TORII_DATABASE_URL`` and
all other ``TORII_`` settings just like the API server does.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from torii_api.auth.security import hash_password
from torii_api.config import get_settings
from torii_api.db.engine import create_engine, create_session_factory, to_async_url
from torii_api.db.models import User, UserRole


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="torii-createadmin",
        description="Create an admin user for the Torii platform.",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address for the admin account.",
    )
    parser.add_argument(
        "--role",
        default=UserRole.ADMIN,
        choices=[r.value for r in UserRole],
        help="Role to assign (default: admin).",
    )
    parser.add_argument(
        "--no-input",
        action="store_true",
        help="Read password from TORII_ADMIN_PASSWORD env var (for CI/scripts).",
    )
    return parser.parse_args(argv)


def prompt_password() -> str:
    pw = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if pw != confirm:
        print("Error: passwords do not match.", file=sys.stderr)
        sys.exit(1)
    if len(pw) < 8:
        print("Error: password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)
    return pw


async def create_user(email: str, password: str, role: str) -> None:
    settings = get_settings()
    engine = create_engine(to_async_url(settings.database_url))
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"Error: user '{email}' already exists.", file=sys.stderr)
            await engine.dispose()
            sys.exit(1)

        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print(f"Error: user '{email}' already exists.", file=sys.stderr)
            await engine.dispose()
            sys.exit(1)

        await engine.dispose()
        print(f"✓ Created {role} user: {email} (id={user.id})")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.no_input:
        import os

        password = os.environ.get("TORII_ADMIN_PASSWORD")
        if not password:
            print(
                "Error: --no-input requires TORII_ADMIN_PASSWORD env var.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        password = prompt_password()

    asyncio.run(create_user(args.email, password, args.role))


if __name__ == "__main__":
    main()
