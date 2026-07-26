"""Password hashing and JWT access-token helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from torii_api.config import Settings


def hash_password(plain: str) -> str:
    """Return a bcrypt hash for ``plain``."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, password_hash: str) -> bool:
    """Check ``plain`` against a stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), password_hash.encode())


def create_access_token(
    *,
    user_id: int,
    role: str,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed JWT bearer token for ``user_id``."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, str | int]:
    """Decode and validate a JWT; raises ``jwt.PyJWTError`` on failure."""
    raw = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    return {"sub": str(raw["sub"]), "role": str(raw["role"])}
