"""add is_archived column to cases

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    if "is_archived" not in {column["name"] for column in sa.inspect(bind).get_columns("cases")}:
        with op.batch_alter_table("cases") as batch_op:
            batch_op.add_column(
                sa.Column("is_archived", sa.Boolean(), server_default="0", nullable=False)
            )


def downgrade() -> None:
    bind = op.get_bind()
    if "is_archived" in {column["name"] for column in sa.inspect(bind).get_columns("cases")}:
        with op.batch_alter_table("cases") as batch_op:
            batch_op.drop_column("is_archived")
