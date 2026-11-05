"""Add case_appointments table for the in-person filing track (Phase 3).

The in-person track (Saudi Arabia consular / Tasheer filing) needs a
record for the visa-centre appointment flow: the applicant requests a
preferred slot, ops complete the booking on vc.tasheer.com, and the
confirmed slot + centre reference are stored on the case for the audit
report and the dossier packet.

Idempotent like 0022: inspect first and create only when missing, so
deployments already carrying the table (e.g. local SQLite provisioned
from models) upgrade cleanly.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | None = None
depends_on: str | None = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("case_appointments"):
        return
    op.create_table(
        "case_appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="requested",
        ),
        sa.Column("centre", sa.String(length=256), nullable=False),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_time_window", sa.String(length=64), nullable=True),
        sa.Column("appointment_date", sa.Date(), nullable=True),
        sa.Column("appointment_time", sa.String(length=32), nullable=True),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_case_appointments_case_id", "case_appointments", ["case_id"])
    op.create_index("ix_case_appointments_status", "case_appointments", ["status"])


def downgrade() -> None:
    if not _has_table("case_appointments"):
        return
    op.drop_index("ix_case_appointments_status", table_name="case_appointments")
    op.drop_index("ix_case_appointments_case_id", table_name="case_appointments")
    op.drop_table("case_appointments")
