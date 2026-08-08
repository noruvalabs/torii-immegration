"""SQLAlchemy declarative base and shared column conventions.

No schema is bound to the metadata on purpose: the same models must run on SQLite (which has
no schemas) and on Postgres. Deployment-time schema namespacing, if wanted, is a Postgres-only
concern handled in migrations — never in the model layer.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """``DateTime(timezone=True)`` that survives SQLite's tzinfo-stripping round-trip.

    Postgres preserves the UTC offset natively; SQLite has no tz-aware storage, so it silently
    returns a naive datetime on read even though an aware one was stored — breaking any
    downstream comparison against a fresh ``datetime.now(UTC)`` (``TypeError: can't compare
    offset-naive and offset-aware datetimes``). Every value ever written through this column is
    already UTC (app code writes ``datetime.now(UTC)``; ``server_default=func.now()`` is
    ``CURRENT_TIMESTAMP``, UTC on SQLite), so a naive value read back just needs its tzinfo
    restored, not converted.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

# Explicit, dialect-portable constraint naming so Alembic autogenerate produces stable names
# on both SQLite and Postgres (and so batch ALTER on SQLite can reference them).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for every Torii model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """``created_at`` / ``updated_at`` maintained by the database clock.

    ``func.now()`` compiles to ``CURRENT_TIMESTAMP`` on SQLite and ``now()`` on Postgres, so
    the same mapping is correct on both engines.
    """

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
