"""add username, email verification, and password reset fields to users

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("email_verified", sa.Boolean(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("email_verification_token", sa.String(length=128), nullable=True)
        )
        batch_op.add_column(sa.Column("password_reset_token", sa.String(length=128), nullable=True))
        batch_op.add_column(
            sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_unique_constraint(batch_op.f("uq_users_username"), ["username"])
        batch_op.create_index(batch_op.f("ix_users_username"), ["username"], unique=True)
        batch_op.create_index(
            batch_op.f("ix_users_email_verification_token"),
            ["email_verification_token"],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f("ix_users_password_reset_token"),
            ["password_reset_token"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_password_reset_token"))
        batch_op.drop_index(batch_op.f("ix_users_email_verification_token"))
        batch_op.drop_index(batch_op.f("ix_users_username"))
        batch_op.drop_constraint(batch_op.f("uq_users_username"), type_="unique")
        batch_op.drop_column("password_reset_expires")
        batch_op.drop_column("password_reset_token")
        batch_op.drop_column("email_verification_token")
        batch_op.drop_column("email_verified")
        batch_op.drop_column("username")
