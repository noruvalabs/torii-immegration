"""initial schema: jurisdictions, cases, outbox_events

Revision ID: 0001
Revises:
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jurisdictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_live", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jurisdictions")),
        sa.UniqueConstraint("code", name=op.f("uq_jurisdictions_code")),
    )
    op.create_index(op.f("ix_jurisdictions_code"), "jurisdictions", ["code"], unique=True)

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("jurisdiction_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("applicant_email", sa.String(length=320), nullable=True),
        sa.Column("renewal_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdictions.id"],
            name=op.f("fk_cases_jurisdiction_id_jurisdictions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
        sa.UniqueConstraint("reference", name=op.f("uq_cases_reference")),
    )
    op.create_index(op.f("ix_cases_reference"), "cases", ["reference"], unique=True)
    op.create_index(op.f("ix_cases_jurisdiction_id"), "cases", ["jurisdiction_id"], unique=False)

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(op.f("ix_outbox_events_topic"), "outbox_events", ["topic"], unique=False)
    op.create_index(
        op.f("ix_outbox_events_processed_at"), "outbox_events", ["processed_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_events_processed_at"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_topic"), table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(op.f("ix_cases_jurisdiction_id"), table_name="cases")
    op.drop_index(op.f("ix_cases_reference"), table_name="cases")
    op.drop_table("cases")
    op.drop_index(op.f("ix_jurisdictions_code"), table_name="jurisdictions")
    op.drop_table("jurisdictions")
