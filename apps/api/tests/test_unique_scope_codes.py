"""Migration 0016: two rows sharing a code is an ambiguous address, not a duplicate record.

A code is how everything reaches a route — case scoping, packs, pack overrides. The tables
never had a unique index over (jurisdiction_id, code), so the 409 branches were catching an
``IntegrityError`` that could not be raised and duplicates were created silently. Adding the
index would fail on a database that already holds one, so 0016 collapses first.

These tests run the migration against a database seeded with the duplicates it exists to
clean up, and check that nothing which pointed at a losing row was left dangling.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


@pytest.fixture
def migrated_to_0015(tmp_path):
    """A file-backed SQLite database at revision 0015, plus its alembic config."""
    db_path = tmp_path / "collapse.db"
    cfg = Config("alembic.ini")
    # env.py drives migrations through an async engine and uses a configured URL verbatim,
    # so the driver has to be named here; the assertions below read it back synchronously.
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    command.upgrade(cfg, "0015")
    engine = create_engine(f"sqlite:///{db_path}")
    yield cfg, engine
    engine.dispose()


def _seed_duplicates(engine) -> dict[str, int]:
    """Two visa_categories sharing 'work', with rows of every kind pointing at each."""
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
        jid = conn.execute(text("SELECT id FROM jurisdictions")).scalar_one()

        ids = []
        for name in ("The keeper", "The duplicate"):
            conn.execute(
                text(
                    "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                    " VALUES (:j, 'work', :n, 1)"
                ),
                {"j": jid, "n": name},
            )
            ids.append(conn.execute(text("SELECT MAX(id) FROM visa_categories")).scalar_one())
        keeper, loser = ids

        conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                " VALUES (:j, 'renewal', 'Renewal', 1)"
            ),
            {"j": jid},
        )
        action = conn.execute(text("SELECT MAX(id) FROM case_actions")).scalar_one()

        # A case, and a definition row, both addressing the losing category.
        conn.execute(
            text(
                "INSERT INTO cases (reference, jurisdiction_id, visa_category_id,"
                " case_action_id, status) VALUES ('JP-2026-000001', :j, :v, :a, 'draft')"
            ),
            {"j": jid, "v": loser, "a": action},
        )
        conn.execute(
            text(
                "INSERT INTO intake_definitions (jurisdiction_id, visa_category_id,"
                " case_action_id, questions, is_live) VALUES (:j, :v, :a, '[]', 1)"
            ),
            {"j": jid, "v": loser, "a": action},
        )

        # Two overrides on the same path: one on each category. Repointing the loser's would
        # collide with the keeper's, so it must be dropped rather than moved.
        for cat in (keeper, loser):
            conn.execute(
                text(
                    "INSERT INTO pack_overrides (jurisdiction_id, visa_category_id,"
                    " case_action_id, path, value, reason, created_by)"
                    " VALUES (:j, :v, :a, 'intake.questions[key=x].prompt', '\"v\"', '', '')"
                ),
                {"j": jid, "v": cat, "a": action},
            )
        # And one on a path the keeper does not have, which must survive by moving.
        conn.execute(
            text(
                "INSERT INTO pack_overrides (jurisdiction_id, visa_category_id,"
                " case_action_id, path, value, reason, created_by)"
                " VALUES (:j, :v, :a, 'documents[code=y].name.en', '\"v\"', '', '')"
            ),
            {"j": jid, "v": loser, "a": action},
        )

    return {"jurisdiction": jid, "keeper": keeper, "loser": loser, "action": action}


def test_the_migration_collapses_duplicates_and_leaves_nothing_dangling(
    migrated_to_0015,
) -> None:
    cfg, engine = migrated_to_0015
    seeded = _seed_duplicates(engine)
    keeper, loser = seeded["keeper"], seeded["loser"]

    command.upgrade(cfg, "0016")

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, name FROM visa_categories WHERE code = 'work'")
        ).fetchall()
        assert [r[0] for r in rows] == [keeper], "the lowest id survives"
        assert rows[0][1] == "The keeper", "and keeps its own name"

        # Everything that addressed the loser now addresses the keeper.
        assert conn.execute(text("SELECT visa_category_id FROM cases")).scalar_one() == keeper
        assert (
            conn.execute(text("SELECT visa_category_id FROM intake_definitions")).scalar_one()
            == keeper
        )

        overrides = conn.execute(
            text("SELECT path, visa_category_id FROM pack_overrides ORDER BY path")
        ).fetchall()
        # The colliding one was dropped, the unique one moved, and both now point at the keeper.
        assert [(p, v) for p, v in overrides] == [
            ("documents[code=y].name.en", keeper),
            ("intake.questions[key=x].prompt", keeper),
        ]
        assert (
            conn.execute(
                text("SELECT COUNT(*) FROM pack_overrides WHERE visa_category_id = :l"),
                {"l": loser},
            ).scalar_one()
            == 0
        )


def test_the_index_then_refuses_a_second_row_with_the_same_code(migrated_to_0015) -> None:
    from sqlalchemy.exc import IntegrityError

    cfg, engine = migrated_to_0015
    _seed_duplicates(engine)
    command.upgrade(cfg, "0016")

    jid = 1
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                    " VALUES (:j, 'work', 'A third one', 1)"
                ),
                {"j": jid},
            )

    # A different jurisdiction may of course reuse the code.
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('UK', 'UK', 1)"))
        other = conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'UK'")).scalar_one()
        conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                " VALUES (:j, 'work', 'Skilled Worker', 1)"
            ),
            {"j": other},
        )


def test_the_migration_is_a_no_op_on_a_database_with_no_duplicates(migrated_to_0015) -> None:
    """The common case: nothing to collapse, and the index simply appears."""
    cfg, engine = migrated_to_0015
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
        for code in ("work", "student"):
            conn.execute(
                text(
                    "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                    " VALUES (1, :c, :c, 1)"
                ),
                {"c": code},
            )

    command.upgrade(cfg, "0016")

    with engine.begin() as conn:
        codes = [r[0] for r in conn.execute(text("SELECT code FROM visa_categories ORDER BY code"))]
    assert codes == ["student", "work"]


def test_downgrade_drops_the_index_and_upgrade_puts_it_back(migrated_to_0015) -> None:
    cfg, engine = migrated_to_0015
    command.upgrade(cfg, "0016")

    def index_names() -> set[str]:
        with engine.begin() as conn:
            return {
                r[0]
                for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'index'"))
            }

    assert "uq_visa_categories_jurisdiction_code" in index_names()
    assert "uq_case_actions_jurisdiction_code" in index_names()

    command.downgrade(cfg, "0015")
    assert "uq_visa_categories_jurisdiction_code" not in index_names()

    command.upgrade(cfg, "0016")
    assert "uq_visa_categories_jurisdiction_code" in index_names()
