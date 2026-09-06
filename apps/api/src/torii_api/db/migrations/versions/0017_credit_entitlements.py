"""add credit ledger and entitlement columns

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-23

This migration was originally committed with the already-used revision ID ``0014``. Its
operations are intentionally idempotent so a database that ran that conflicting revision can
join the canonical migration chain without losing data.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    if "credit_balance" not in {column["name"] for column in sa.inspect(bind).get_columns("users")}:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column("credit_balance", sa.Integer(), server_default="10", nullable=False)
            )

    if "is_entitled" not in {column["name"] for column in sa.inspect(bind).get_columns("cases")}:
        with op.batch_alter_table("cases") as batch_op:
            batch_op.add_column(
                sa.Column("is_entitled", sa.Boolean(), server_default="0", nullable=False)
            )

    if "updated_at" not in {
        column["name"] for column in sa.inspect(bind).get_columns("document_wallet_item_versions")
    }:
        with op.batch_alter_table("document_wallet_item_versions") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                )
            )

    if "credit_transactions" not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            "credit_transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("balance_after", sa.Integer(), nullable=False),
            sa.Column("feature", sa.String(length=64), nullable=False),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
            sa.Column("description", sa.String(length=256), nullable=False),
            sa.Column("reference_id", sa.String(length=128), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    existing_indexes = {
        index["name"] for index in sa.inspect(bind).get_indexes("credit_transactions")
    }
    for name, columns in (
        ("ix_credit_transactions_user_id", ["user_id"]),
        ("ix_credit_transactions_case_id", ["case_id"]),
        ("ix_credit_transactions_reference_id", ["reference_id"]),
    ):
        if name not in existing_indexes:
            op.create_index(name, "credit_transactions", columns)


def downgrade() -> None:
    bind = op.get_bind()
    if "credit_transactions" in set(sa.inspect(bind).get_table_names()):
        existing_indexes = {
            index["name"] for index in sa.inspect(bind).get_indexes("credit_transactions")
        }
        for name in (
            "ix_credit_transactions_reference_id",
            "ix_credit_transactions_case_id",
            "ix_credit_transactions_user_id",
        ):
            if name in existing_indexes:
                op.drop_index(name, table_name="credit_transactions")
        op.drop_table("credit_transactions")

    if "updated_at" in {
        column["name"] for column in sa.inspect(bind).get_columns("document_wallet_item_versions")
    }:
        with op.batch_alter_table("document_wallet_item_versions") as batch_op:
            batch_op.drop_column("updated_at")

    if "is_entitled" in {column["name"] for column in sa.inspect(bind).get_columns("cases")}:
        with op.batch_alter_table("cases") as batch_op:
            batch_op.drop_column("is_entitled")

    if "credit_balance" in {column["name"] for column in sa.inspect(bind).get_columns("users")}:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("credit_balance")
