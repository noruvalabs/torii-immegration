"""SQLAlchemy declarative base and shared column conventions.

No schema is bound to the metadata on purpose: the same models must run on SQLite (which has
no schemas) and on Postgres. Deployment-time schema namespacing, if wanted, is a Postgres-only
concern handled in migrations — never in the model layer.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
