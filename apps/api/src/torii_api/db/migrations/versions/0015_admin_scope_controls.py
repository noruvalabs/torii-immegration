"""add the admin on/off switch and discovery provenance to scope tables

``is_enabled`` is the admin's own switch, separate from ``is_live`` because ``seed()``
rewrites ``is_live`` from ``docs/jurisdictions`` on every run. ``description`` / ``source``
/ ``citation`` record what scope discovery read off an official page.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Existing rows predate the switch and were all being offered, so they default to on;
# turning something off has to stay a deliberate act by an admin, not a side effect of
# running the migration.
_SCOPE_TABLES = ("visa_categories", "case_actions")


def upgrade() -> None:
    with op.batch_alter_table("jurisdictions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_enabled", sa.Boolean(), server_default="1", nullable=False)
        )

    for table in _SCOPE_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_enabled", sa.Boolean(), server_default="1", nullable=False)
            )
            batch_op.add_column(
                sa.Column("description", sa.String(length=512), server_default="", nullable=False)
            )
            batch_op.add_column(
                sa.Column("source", sa.String(length=16), server_default="manual", nullable=False)
            )
            batch_op.add_column(
                sa.Column("citation", sa.JSON(), server_default="{}", nullable=False)
            )


def downgrade() -> None:
    for table in _SCOPE_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("citation")
            batch_op.drop_column("source")
            batch_op.drop_column("description")
            batch_op.drop_column("is_enabled")

    with op.batch_alter_table("jurisdictions", schema=None) as batch_op:
        batch_op.drop_column("is_enabled")
