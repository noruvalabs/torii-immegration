"""add case prior_application continuity facts

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("prior_application", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "prior_application")
