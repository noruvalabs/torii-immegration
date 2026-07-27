"""add intake_answers and intake_step to cases for save/resume (US-03)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("intake_answers", sa.JSON(), nullable=False, server_default="{}")
        )
        batch_op.add_column(sa.Column("intake_step", sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.drop_column("intake_step")
        batch_op.drop_column("intake_answers")
