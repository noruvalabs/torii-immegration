"""add pack_overrides (admin edits that survive a reseed)

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pack_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jurisdiction_id", sa.Integer(), nullable=False),
        sa.Column("visa_category_id", sa.Integer(), nullable=False),
        sa.Column("case_action_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=256), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=256), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["jurisdiction_id"], ["jurisdictions.id"]),
        sa.ForeignKeyConstraint(["visa_category_id"], ["visa_categories.id"]),
        sa.ForeignKeyConstraint(["case_action_id"], ["case_actions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pack_overrides_jurisdiction_id", "pack_overrides", ["jurisdiction_id"])
    op.create_index("ix_pack_overrides_visa_category_id", "pack_overrides", ["visa_category_id"])
    op.create_index("ix_pack_overrides_case_action_id", "pack_overrides", ["case_action_id"])
    op.create_index("ix_pack_overrides_path", "pack_overrides", ["path"])
    # One live edit per path per scope. Two rows editing the same value would apply in
    # whichever order the query returned them, which is not an answer to "what is live".
    op.create_index(
        "uq_pack_overrides_scope_path",
        "pack_overrides",
        ["jurisdiction_id", "visa_category_id", "case_action_id", "path"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_pack_overrides_scope_path", table_name="pack_overrides")
    op.drop_index("ix_pack_overrides_path", table_name="pack_overrides")
    op.drop_index("ix_pack_overrides_case_action_id", table_name="pack_overrides")
    op.drop_index("ix_pack_overrides_visa_category_id", table_name="pack_overrides")
    op.drop_index("ix_pack_overrides_jurisdiction_id", table_name="pack_overrides")
    op.drop_table("pack_overrides")
