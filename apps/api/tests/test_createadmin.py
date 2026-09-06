import pytest
from sqlalchemy import select

from torii_api.auth.security import verify_password
from torii_api.db.models import User, UserRole
from torii_api.management.createadmin import ensure_admin_user


@pytest.mark.asyncio
async def test_ensure_admin_user_creates_and_is_idempotent(tmp_path):
    db_path = tmp_path / "test_admin.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    # 1. Create schema
    from torii_api.db.base import Base
    from torii_api.db.engine import create_engine

    engine = create_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    # 2. First call: creates user
    created = await ensure_admin_user(
        db_url,
        email="superuser@torii.app",
        password="secret-password-123",
    )
    assert created is True

    # Check user in DB
    engine = create_engine(db_url)
    from torii_api.db.engine import create_session_factory

    factory = create_session_factory(engine)
    async with factory() as session:
        user = await session.scalar(select(User).where(User.email == "superuser@torii.app"))
        assert user is not None
        assert user.role == UserRole.ADMIN
        assert user.is_active is True
        assert user.email_verified is True
        assert verify_password("secret-password-123", user.password_hash) is True
    await engine.dispose()

    # 3. Second call: idempotent (returns False, does not duplicate or error)
    created_again = await ensure_admin_user(
        db_url,
        email="superuser@torii.app",
        password="secret-password-123",
    )
    assert created_again is False
