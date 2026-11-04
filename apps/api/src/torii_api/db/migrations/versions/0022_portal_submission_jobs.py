"""Add portal_submission_jobs table for eVisa Submission Bot (Thing 3).

Revision ID: 0022
Revises: 0021
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    if "portal_submission_jobs" not in existing_tables:
        op.create_table(
            "portal_submission_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
            sa.Column("jurisdiction_code", sa.String(8), nullable=False),
            sa.Column("portal_name", sa.String(128), nullable=False),
            sa.Column("portal_url", sa.String(512), nullable=False),
            sa.Column(
                "status",
                sa.String(32),
                server_default="queued",
                nullable=False,
            ),
            sa.Column("attempt_count", sa.Integer(), server_default="1", nullable=False),
            sa.Column("portal_reference", sa.String(128), nullable=True),
            sa.Column("receipt_url", sa.String(512), nullable=True),
            sa.Column("screenshot_url", sa.String(512), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("steps_log", sa.JSON(), nullable=False),
            sa.Column("proxy_used", sa.String(64), nullable=True),
            sa.Column("captcha_solved", sa.Boolean(), server_default="0", nullable=False),
            sa.Column("dispatched_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index(
            "ix_portal_submission_jobs_case_id", "portal_submission_jobs", ["case_id"]
        )
        op.create_index(
            "ix_portal_submission_jobs_jurisdiction_code",
            "portal_submission_jobs",
            ["jurisdiction_code"],
        )
        op.create_index(
            "ix_portal_submission_jobs_status", "portal_submission_jobs", ["status"]
        )


def downgrade() -> None:
    op.drop_table("portal_submission_jobs")

