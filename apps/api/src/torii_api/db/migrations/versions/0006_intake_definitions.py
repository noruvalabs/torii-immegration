"""add intake_definitions table for branching questionnaires (US-02)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intake_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jurisdiction_id", sa.Integer(), nullable=False),
        sa.Column("visa_category_id", sa.Integer(), nullable=False),
        sa.Column("case_action_id", sa.Integer(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("is_live", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdictions.id"],
            name=op.f("fk_intake_definitions_jurisdiction_id_jurisdictions"),
        ),
        sa.ForeignKeyConstraint(
            ["visa_category_id"],
            ["visa_categories.id"],
            name=op.f("fk_intake_definitions_visa_category_id_visa_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["case_action_id"],
            ["case_actions.id"],
            name=op.f("fk_intake_definitions_case_action_id_case_actions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intake_definitions")),
    )
    op.create_index(
        op.f("ix_intake_definitions_jurisdiction_id"),
        "intake_definitions",
        ["jurisdiction_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intake_definitions_visa_category_id"),
        "intake_definitions",
        ["visa_category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intake_definitions_case_action_id"),
        "intake_definitions",
        ["case_action_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_intake_definitions_case_action_id"), table_name="intake_definitions")
    op.drop_index(op.f("ix_intake_definitions_visa_category_id"), table_name="intake_definitions")
    op.drop_index(op.f("ix_intake_definitions_jurisdiction_id"), table_name="intake_definitions")
    op.drop_table("intake_definitions")
