"""add email_verification_expires column to users

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    if "email_verification_expires" not in {
        column["name"] for column in sa.inspect(bind).get_columns("users")
    }:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column("email_verification_expires", sa.DateTime(timezone=True), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    if "email_verification_expires" in {
        column["name"] for column in sa.inspect(bind).get_columns("users")
    }:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("email_verification_expires")
