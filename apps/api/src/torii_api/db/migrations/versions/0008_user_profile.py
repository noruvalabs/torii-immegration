"""add user profile fields

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=200), nullable=True))
    op.add_column("users", sa.Column("nationality", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("passport_number", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("passport_expiry", sa.String(length=16), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.String(length=16), nullable=True))
    op.add_column("users", sa.Column("current_country", sa.String(length=100), nullable=True))
    op.add_column(
        "users",
        sa.Column("profile_complete", sa.Boolean(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "profile_complete")
    op.drop_column("users", "current_country")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "passport_expiry")
    op.drop_column("users", "passport_number")
    op.drop_column("users", "nationality")
    op.drop_column("users", "full_name")
