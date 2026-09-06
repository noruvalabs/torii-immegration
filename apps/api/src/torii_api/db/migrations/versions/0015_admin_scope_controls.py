"""add the admin on/off switch and discovery provenance to scope tables

``is_enabled`` is the admin's own switch, separate from ``is_live`` because ``seed()``
rewrites ``is_live`` from ``docs/jurisdictions`` on every run. ``description`` / ``source``
/ ``citation`` record what scope discovery read off an official page.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-31

The short-lived credit branch also shipped a different migration as ``0014``. A database
created from that branch is stamped ``0014`` but has credit columns instead of
``pack_overrides``. The compatibility step below restores the canonical 0014 schema before
continuing, so developers can upgrade without deleting their local data.
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

_PACK_OVERRIDE_INDEXES = (
    ("ix_pack_overrides_jurisdiction_id", ["jurisdiction_id"], False),
    ("ix_pack_overrides_visa_category_id", ["visa_category_id"], False),
    ("ix_pack_overrides_case_action_id", ["case_action_id"], False),
    ("ix_pack_overrides_path", ["path"], False),
    (
        "uq_pack_overrides_scope_path",
        ["jurisdiction_id", "visa_category_id", "case_action_id", "path"],
        True,
    ),
)


def _ensure_pack_overrides() -> None:
    """Repair databases stamped by the conflicting credit migration formerly named 0014."""
    bind = op.get_bind()
    table_names = set(sa.inspect(bind).get_table_names())
    if "pack_overrides" not in table_names:
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
            sa.ForeignKeyConstraint(["jurisdiction_id"], ["jurisdictions.id"]),
            sa.ForeignKeyConstraint(["visa_category_id"], ["visa_categories.id"]),
            sa.ForeignKeyConstraint(["case_action_id"], ["case_actions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("pack_overrides")}
    for name, columns, unique in _PACK_OVERRIDE_INDEXES:
        if name not in existing_indexes:
            op.create_index(name, "pack_overrides", columns, unique=unique)


def upgrade() -> None:
    _ensure_pack_overrides()

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
