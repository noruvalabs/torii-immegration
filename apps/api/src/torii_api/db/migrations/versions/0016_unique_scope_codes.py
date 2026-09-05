"""collapse duplicate scope codes, then make (jurisdiction, code) unique

``visa_categories`` and ``case_actions`` never had a unique index over
(jurisdiction_id, code), so the 409 branches in ``api/jurisdictions.py`` were catching an
``IntegrityError`` that could not be raised, and duplicates were created silently. A code
is how everything addresses a route — case scoping, content packs, pack overrides, the
applicant's URL — so two rows sharing one is not a duplicate record, it is an ambiguous
address, and which row answers depends on query order.

Adding the index alone would fail on any database that already holds a duplicate. So this
collapses each group onto its lowest id first, repointing everything that referenced a
loser. Definition rows (intake, eligibility, documents, forms, research) are repointed
rather than deleted: a duplicate definition is something the read path already tolerates,
where losing a definition is content gone. ``pack_overrides`` is the exception — it has its
own unique index over (scope, path), so a repoint that would collide there drops the loser
and keeps the override already attached to the surviving scope.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every table that addresses a scope row, and the column it does it through. Repointed in
# this order; ``pack_overrides`` is handled separately because of its own unique index.
_REFERENCES: dict[str, tuple[tuple[str, str], ...]] = {
    "visa_categories": (
        ("intake_definitions", "visa_category_id"),
        ("eligibility_rule_sets", "visa_category_id"),
        ("document_requirement_sets", "visa_category_id"),
        ("form_templates", "visa_category_id"),
        ("scope_research", "visa_category_id"),
        ("cases", "visa_category_id"),
    ),
    "case_actions": (
        ("intake_definitions", "case_action_id"),
        ("eligibility_rule_sets", "case_action_id"),
        ("document_requirement_sets", "case_action_id"),
        ("form_templates", "case_action_id"),
        ("scope_research", "case_action_id"),
        ("cases", "case_action_id"),
    ),
}

# ``pack_overrides`` is unique over (jurisdiction_id, visa_category_id, case_action_id, path).
# Repointing one of those two columns collides when the other one, and the path, already
# match a row on the keeper — so both are named here, not just the one being repointed.
_OVERRIDE_COLUMNS = {
    "visa_categories": ("visa_category_id", "case_action_id"),
    "case_actions": ("case_action_id", "visa_category_id"),
}

_INDEX_NAME = {
    "visa_categories": "uq_visa_categories_jurisdiction_code",
    "case_actions": "uq_case_actions_jurisdiction_code",
}


def _collapse_duplicates(bind: sa.engine.Connection, table: str) -> None:
    """Point every reference at the lowest id in each (jurisdiction_id, code) group."""
    groups = bind.execute(
        sa.text(
            f"SELECT jurisdiction_id, code, MIN(id) AS keeper, COUNT(*) AS n"  # noqa: S608
            f" FROM {table} GROUP BY jurisdiction_id, code HAVING COUNT(*) > 1"
        )
    ).fetchall()

    for jurisdiction_id, code, keeper, _count in groups:
        losers = [
            row[0]
            for row in bind.execute(
                sa.text(
                    f"SELECT id FROM {table}"  # noqa: S608
                    " WHERE jurisdiction_id = :j AND code = :c AND id <> :keep"
                ),
                {"j": jurisdiction_id, "c": code, "keep": keeper},
            )
        ]
        if not losers:
            continue

        for ref_table, column in _REFERENCES[table]:
            bind.execute(
                sa.text(
                    f"UPDATE {ref_table} SET {column} = :keep"  # noqa: S608
                    f" WHERE {column} IN :losers"
                ).bindparams(sa.bindparam("losers", expanding=True)),
                {"keep": keeper, "losers": losers},
            )

        # An override whose repointed (scope, path) already exists on the keeper would break
        # pack_overrides' own unique index, so it is dropped in favour of the one already
        # there. Everything else repoints.
        moved, other = _OVERRIDE_COLUMNS[table]
        bind.execute(
            sa.text(
                f"DELETE FROM pack_overrides WHERE {moved} IN :losers"  # noqa: S608
                " AND EXISTS ("
                "   SELECT 1 FROM pack_overrides AS kept"
                "   WHERE kept.jurisdiction_id = pack_overrides.jurisdiction_id"
                "     AND kept.path = pack_overrides.path"
                f"    AND kept.{moved} = :keep"
                f"    AND kept.{other} = pack_overrides.{other}"
                " )"
            ).bindparams(sa.bindparam("losers", expanding=True)),
            {"keep": keeper, "losers": losers},
        )
        bind.execute(
            sa.text(
                f"UPDATE pack_overrides SET {moved} = :keep WHERE {moved} IN :losers"  # noqa: S608
            ).bindparams(sa.bindparam("losers", expanding=True)),
            {"keep": keeper, "losers": losers},
        )

        bind.execute(
            sa.text(f"DELETE FROM {table} WHERE id IN :losers").bindparams(  # noqa: S608
                sa.bindparam("losers", expanding=True)
            ),
            {"losers": losers},
        )


def upgrade() -> None:
    bind = op.get_bind()
    for table in ("visa_categories", "case_actions"):
        _collapse_duplicates(bind, table)
        op.create_index(
            _INDEX_NAME[table],
            table,
            ["jurisdiction_id", "code"],
            unique=True,
        )


def downgrade() -> None:
    # Collapsing is not reversible — the losing rows are gone. Dropping the index is all
    # there is to undo.
    for table in ("visa_categories", "case_actions"):
        op.drop_index(_INDEX_NAME[table], table_name=table)
