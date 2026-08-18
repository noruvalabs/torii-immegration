"""add scope_research and cross-border case fields

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "visa_categories",
        sa.Column("research_enabled", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column(
        "case_actions",
        sa.Column("research_enabled", sa.Boolean(), server_default="0", nullable=False),
    )

    op.create_table(
        "scope_research",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jurisdiction_id", sa.Integer(), nullable=False),
        sa.Column("visa_category_id", sa.Integer(), nullable=False),
        sa.Column("case_action_id", sa.Integer(), nullable=False),
        sa.Column("origin_country", sa.String(length=8), nullable=True),
        sa.Column("residence_country", sa.String(length=8), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="queued",
            nullable=False,
        ),
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
            ["jurisdiction_id"],
            ["jurisdictions.id"],
            name=op.f("fk_scope_research_jurisdiction_id_jurisdictions"),
        ),
        sa.ForeignKeyConstraint(
            ["visa_category_id"],
            ["visa_categories.id"],
            name=op.f("fk_scope_research_visa_category_id_visa_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["case_action_id"],
            ["case_actions.id"],
            name=op.f("fk_scope_research_case_action_id_case_actions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scope_research")),
    )
    for column in ("jurisdiction_id", "visa_category_id", "case_action_id"):
        op.create_index(
            op.f(f"ix_scope_research_{column}"),
            "scope_research",
            [column],
            unique=False,
        )

    # Cross-border case fields + link to the research snapshot.
    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("origin_country", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("residence_country", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("research_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_cases_origin_country"), ["origin_country"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_cases_residence_country"), ["residence_country"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_cases_research_id"), ["research_id"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_cases_research_id_scope_research"),
            "scope_research",
            ["research_id"],
            ["id"],
        )

    # Research-driven forms have no FormTemplate row; allow research_id instead.
    with op.batch_alter_table("case_generated_forms", schema=None) as batch_op:
        batch_op.alter_column(
            "form_template_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("research_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_case_generated_forms_research_id"),
            ["research_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_case_generated_forms_research_id_scope_research"),
            "scope_research",
            ["research_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("case_generated_forms", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("fk_case_generated_forms_research_id_scope_research"),
            type_="foreignkey",
        )
        batch_op.drop_index(batch_op.f("ix_case_generated_forms_research_id"))
        batch_op.drop_column("research_id")
        batch_op.alter_column(
            "form_template_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("fk_cases_research_id_scope_research"), type_="foreignkey"
        )
        batch_op.drop_index(batch_op.f("ix_cases_research_id"))
        batch_op.drop_index(batch_op.f("ix_cases_residence_country"))
        batch_op.drop_index(batch_op.f("ix_cases_origin_country"))
        batch_op.drop_column("research_id")
        batch_op.drop_column("residence_country")
        batch_op.drop_column("origin_country")

    for column in ("case_action_id", "visa_category_id", "jurisdiction_id"):
        op.drop_index(op.f(f"ix_scope_research_{column}"), table_name="scope_research")
    op.drop_table("scope_research")

    op.drop_column("case_actions", "research_enabled")
    op.drop_column("visa_categories", "research_enabled")
