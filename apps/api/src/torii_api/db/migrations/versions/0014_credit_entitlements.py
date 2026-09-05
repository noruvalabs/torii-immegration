"""add credit ledger and entitlement columns

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-23
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
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("credit_balance", sa.Integer(), server_default="10", nullable=False)
        )

    with op.batch_alter_table("cases") as batch_op:
        batch_op.add_column(
            sa.Column("is_entitled", sa.Boolean(), server_default="0", nullable=False)
        )

    with op.batch_alter_table("document_wallet_item_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )

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
    op.create_index("ix_credit_transactions_user_id", "credit_transactions", ["user_id"])
    op.create_index("ix_credit_transactions_case_id", "credit_transactions", ["case_id"])
    op.create_index("ix_credit_transactions_reference_id", "credit_transactions", ["reference_id"])


def downgrade() -> None:
    op.drop_index("ix_credit_transactions_reference_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_case_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_user_id", table_name="credit_transactions")
    op.drop_table("credit_transactions")

    with op.batch_alter_table("document_wallet_item_versions") as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("cases") as batch_op:
        batch_op.drop_column("is_entitled")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("credit_balance")
