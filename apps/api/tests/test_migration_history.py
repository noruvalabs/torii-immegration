"""Regression coverage for the migration graph and the former duplicate 0014 revision."""

from __future__ import annotations

from importlib import import_module

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


def _config(tmp_path, name: str) -> tuple[Config, str]:
    db_path = tmp_path / name
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return cfg, str(db_path)


def _assert_complete_schema(db_path: str) -> None:
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        schema = inspect(engine)
        assert "pack_overrides" in schema.get_table_names()
        assert "credit_transactions" in schema.get_table_names()
        assert "credit_balance" in {column["name"] for column in schema.get_columns("users")}
        assert "is_entitled" in {column["name"] for column in schema.get_columns("cases")}
        assert "is_enabled" in {column["name"] for column in schema.get_columns("jurisdictions")}
        assert "uq_visa_categories_jurisdiction_code" in {
            index["name"] for index in schema.get_indexes("visa_categories")
        }
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "0017"
    finally:
        engine.dispose()


def test_migration_history_has_one_head() -> None:
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["0017"]


def test_fresh_database_upgrades_to_head(tmp_path) -> None:
    cfg, db_path = _config(tmp_path, "fresh.db")
    command.upgrade(cfg, "head")
    _assert_complete_schema(db_path)


def test_database_stamped_by_the_conflicting_credit_0014_is_repaired(tmp_path) -> None:
    cfg, db_path = _config(tmp_path, "conflicting-credit-0014.db")
    command.upgrade(cfg, "0013")

    # Recreate the state produced by the short-lived branch: credit schema was applied, but
    # the version table was stamped 0014 even though canonical 0014 owns pack_overrides.
    credit_revision = import_module("torii_api.db.migrations.versions.0017_credit_entitlements")
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as connection:
            migration_context = MigrationContext.configure(connection)
            with Operations.context(migration_context):
                credit_revision.upgrade()
            connection.execute(text("UPDATE alembic_version SET version_num = '0014'"))
    finally:
        engine.dispose()

    command.upgrade(cfg, "head")
    _assert_complete_schema(db_path)
