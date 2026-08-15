"""add case_stage_research (agentic per-stage research engine)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_stage_research",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("scope_key", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source_pages", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("researched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_case_stage_research_case_id_cases")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_stage_research")),
        sa.UniqueConstraint("case_id", "stage", name="uq_case_stage_research_case"),
        sa.UniqueConstraint("scope_key", "stage", name="uq_case_stage_research_scope"),
    )
    op.create_index(
        op.f("ix_case_stage_research_case_id"), "case_stage_research", ["case_id"], unique=False
    )
    op.create_index(
        op.f("ix_case_stage_research_stage"), "case_stage_research", ["stage"], unique=False
    )
    op.create_index(
        op.f("ix_case_stage_research_scope_key"),
        "case_stage_research",
        ["scope_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_case_stage_research_scope_key"), table_name="case_stage_research")
    op.drop_index(op.f("ix_case_stage_research_stage"), table_name="case_stage_research")
    op.drop_index(op.f("ix_case_stage_research_case_id"), table_name="case_stage_research")
    op.drop_table("case_stage_research")
