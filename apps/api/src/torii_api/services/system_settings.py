"""System settings service for runtime configuration."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.config import get_settings
from torii_api.db.models import SystemSetting


async def get_system_setting(
    session: AsyncSession,
    key: str,
    default: Any = None,
) -> Any:
    """Retrieve a system setting by key, returning `default` if not set."""
    result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is not None:
        return setting.value_json
    return default


async def set_system_setting(
    session: AsyncSession,
    key: str,
    value: Any,
    description: str | None = None,
) -> SystemSetting:
    """Create or update a system setting by key."""
    result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = SystemSetting(key=key, value_json=value, description=description)
        session.add(setting)
    else:
        setting.value_json = value
        if description is not None:
            setting.description = description
    await session.commit()
    await session.refresh(setting)
    return setting


async def is_payments_enabled(session: AsyncSession) -> bool:
    """Return True if payments are globally enabled on the platform."""
    settings = get_settings()
    stored = await get_system_setting(session, "payments_enabled", default=None)
    if stored is not None:
        return bool(stored)
    return bool(settings.payments_enabled_default)


async def set_payments_enabled(session: AsyncSession, enabled: bool) -> bool:
    """Toggle online payments on or off across the platform."""
    await set_system_setting(
        session,
        "payments_enabled",
        value=enabled,
        description="Global switch to enable or disable applicant online payments and credit checkout",
    )
    return enabled
