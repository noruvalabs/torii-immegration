"""add paddle payment checkouts, webhook events, and system settings tables

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    # 1. system_settings
    if "system_settings" not in existing_tables:
        op.create_table(
            "system_settings",
            sa.Column("key", sa.String(length=64), primary_key=True),
            sa.Column("value_json", sa.JSON(), nullable=False),
            sa.Column("description", sa.String(length=256), nullable=True),
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

    # 2. payment_checkouts
    if "payment_checkouts" not in existing_tables:
        op.create_table(
            "payment_checkouts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("pack_id", sa.String(length=32), nullable=False),
            sa.Column("credits", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
            sa.Column("provider", sa.String(length=32), nullable=False, server_default="paddle"),
            sa.Column("provider_session_id", sa.String(length=255), nullable=True),
            sa.Column("provider_customer_id", sa.String(length=255), nullable=True),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="requires_payment",
            ),
            sa.Column("checkout_url", sa.String(length=1024), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
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
        op.create_index("ix_payment_checkouts_public_id", "payment_checkouts", ["public_id"], unique=True)
        op.create_index("ix_payment_checkouts_user_id", "payment_checkouts", ["user_id"])
        op.create_index("ix_payment_checkouts_pack_id", "payment_checkouts", ["pack_id"])
        op.create_index("ix_payment_checkouts_provider", "payment_checkouts", ["provider"])
        op.create_index("ix_payment_checkouts_provider_session_id", "payment_checkouts", ["provider_session_id"], unique=True)
        op.create_index("ix_payment_checkouts_status", "payment_checkouts", ["status"])

    # 3. payment_webhook_events
    if "payment_webhook_events" not in existing_tables:
        op.create_table(
            "payment_webhook_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("event_id", sa.String(length=255), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
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
        op.create_index("ix_payment_webhook_events_provider", "payment_webhook_events", ["provider"])
        op.create_index("ix_payment_webhook_events_event_id", "payment_webhook_events", ["event_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    if "payment_webhook_events" in existing_tables:
        op.drop_table("payment_webhook_events")
    if "payment_checkouts" in existing_tables:
        op.drop_table("payment_checkouts")
    if "system_settings" in existing_tables:
        op.drop_table("system_settings")
