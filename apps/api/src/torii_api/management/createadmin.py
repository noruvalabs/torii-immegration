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
    import os

    default_email = os.environ.get("TORII_SUPERUSER_EMAIL") or os.environ.get("TORII_ADMIN_EMAIL")
    parser = argparse.ArgumentParser(
        prog="torii-createadmin",
        description="Create an admin user for the Torii platform.",
    )
    parser.add_argument(
        "--email",
        default=default_email,
        required=not bool(default_email),
        help="Email address for the admin account (defaults to TORII_SUPERUSER_EMAIL / TORII_ADMIN_EMAIL).",
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
        help="Read password from TORII_SUPERUSER_PASSWORD or TORII_ADMIN_PASSWORD env var.",
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


async def ensure_admin_user(
    database_url: str,
    *,
    email: str,
    password: str,
    role: str = UserRole.ADMIN,
) -> bool:
    """Ensure an admin user exists with the given credentials.

    Returns:
        True if a new user was created, False if user already existed.
    """
    engine = create_engine(to_async_url(database_url))
    session_factory = create_session_factory(engine)

    try:
        async with session_factory() as session:
            normalized_email = email.strip().lower()
            existing = await session.scalar(select(User).where(User.email == normalized_email))
            if existing is not None:
                changed = False
                if existing.role != role:
                    existing.role = role
                    changed = True
                if not existing.is_active:
                    existing.is_active = True
                    changed = True
                if not existing.email_verified:
                    existing.email_verified = True
                    changed = True
                if changed:
                    await session.commit()
                return False

            username = normalized_email.split("@")[0]
            existing_name = await session.scalar(select(User).where(User.username == username))
            if existing_name is not None:
                username = None

            user = User(
                email=normalized_email,
                username=username,
                password_hash=hash_password(password),
                role=role,
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            try:
                await session.commit()
                return True
            except IntegrityError:
                await session.rollback()
                return False
    finally:
        await engine.dispose()


async def create_user(email: str, password: str, role: str) -> None:
    settings = get_settings()
    created = await ensure_admin_user(
        settings.database_url,
        email=email,
        password=password,
        role=role,
    )
    if not created:
        print(f"Error: user '{email}' already exists.", file=sys.stderr)
        sys.exit(1)
    print(f"✓ Created {role} user: {email}")


def main(argv: list[str] | None = None) -> None:
    import os

    args = parse_args(argv)

    env_password = os.environ.get("TORII_SUPERUSER_PASSWORD") or os.environ.get(
        "TORII_ADMIN_PASSWORD"
    )
    if args.no_input or (env_password and not sys.stdin.isatty()):
        password = env_password
        if not password:
            print(
                "Error: --no-input requires TORII_SUPERUSER_PASSWORD or TORII_ADMIN_PASSWORD env var.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        password = env_password if env_password else prompt_password()

    asyncio.run(create_user(args.email, password, args.role))


if __name__ == "__main__":
    main()
