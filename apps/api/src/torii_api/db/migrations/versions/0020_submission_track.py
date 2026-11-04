"""add submission_track column to jurisdictions and visa_categories

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-29
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
    insp = sa.inspect(bind)

    if "submission_track" not in {
        column["name"] for column in insp.get_columns("jurisdictions")
    }:
        with op.batch_alter_table("jurisdictions") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "submission_track",
                    sa.String(length=32),
                    nullable=False,
                    server_default="consular",
                )
            )

    if "submission_track" not in {
        column["name"] for column in insp.get_columns("visa_categories")
    }:
        with op.batch_alter_table("visa_categories") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "submission_track",
                    sa.String(length=32),
                    nullable=True,
                )
            )

    # Set initial well-known tracks
    op.execute(
        sa.text("UPDATE jurisdictions SET submission_track = 'hybrid' WHERE UPPER(code) = 'IN'")
    )
    op.execute(
        sa.text("UPDATE jurisdictions SET submission_track = 'digital' WHERE UPPER(code) IN ('SA', 'VN', 'EG', 'BH', 'KH', 'JO', 'QA', 'LK', 'TR', 'MY')")
    )
    op.execute(
        sa.text("UPDATE jurisdictions SET submission_track = 'hybrid' WHERE UPPER(code) = 'CA'")
    )
    op.execute(
        sa.text("UPDATE jurisdictions SET submission_track = 'consular' WHERE UPPER(code) IN ('JP', 'US', 'GB', 'UK', 'FR', 'DE', 'ES', 'KR')")
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "submission_track" in {
        column["name"] for column in insp.get_columns("visa_categories")
    }:
        with op.batch_alter_table("visa_categories") as batch_op:
            batch_op.drop_column("submission_track")

    if "submission_track" in {
        column["name"] for column in insp.get_columns("jurisdictions")
    }:
        with op.batch_alter_table("jurisdictions") as batch_op:
            batch_op.drop_column("submission_track")

