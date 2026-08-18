"""add visa_categories, case_actions tables and scoping fields to cases

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "visa_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jurisdiction_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
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
            name=op.f("fk_visa_categories_jurisdiction_id_jurisdictions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visa_categories")),
    )
    op.create_index(
        op.f("ix_visa_categories_jurisdiction_id"),
        "visa_categories",
        ["jurisdiction_id"],
        unique=False,
    )
    op.create_index(op.f("ix_visa_categories_code"), "visa_categories", ["code"], unique=False)

    op.create_table(
        "case_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jurisdiction_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
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
            name=op.f("fk_case_actions_jurisdiction_id_jurisdictions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_actions")),
    )
    op.create_index(
        op.f("ix_case_actions_jurisdiction_id"),
        "case_actions",
        ["jurisdiction_id"],
        unique=False,
    )
    op.create_index(op.f("ix_case_actions_code"), "case_actions", ["code"], unique=False)

    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("visa_category_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("case_action_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_cases_visa_category_id"), ["visa_category_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_cases_case_action_id"), ["case_action_id"], unique=False
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_cases_visa_category_id_visa_categories"),
            "visa_categories",
            ["visa_category_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_cases_case_action_id_case_actions"),
            "case_actions",
            ["case_action_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("fk_cases_case_action_id_case_actions"), type_="foreignkey"
        )
        batch_op.drop_constraint(
            batch_op.f("fk_cases_visa_category_id_visa_categories"), type_="foreignkey"
        )
        batch_op.drop_index(batch_op.f("ix_cases_case_action_id"))
        batch_op.drop_index(batch_op.f("ix_cases_visa_category_id"))
        batch_op.drop_column("case_action_id")
        batch_op.drop_column("visa_category_id")

    op.drop_index(op.f("ix_case_actions_code"), table_name="case_actions")
    op.drop_index(op.f("ix_case_actions_jurisdiction_id"), table_name="case_actions")
    op.drop_table("case_actions")

    op.drop_index(op.f("ix_visa_categories_code"), table_name="visa_categories")
    op.drop_index(op.f("ix_visa_categories_jurisdiction_id"), table_name="visa_categories")
    op.drop_table("visa_categories")
