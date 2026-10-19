"""Migrate data from local SQLite (apps/api/torii.db) to Supabase PostgreSQL.

Usage:
    # 1. Dry-run mode (verifies local data without writing to remote):
    python scripts/migrate_sqlite_to_supabase.py --dry-run

    # 2. Using connection string from .env:
    python scripts/migrate_sqlite_to_supabase.py

    # 3. Or providing Supabase connection string explicitly:
    python scripts/migrate_sqlite_to_supabase.py "postgresql://postgres.fffdozvnragwhdqypjzj:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# Ensure apps/api/src is on the import path
REPO_ROOT = Path(__file__).resolve().parent.parent
API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine

from torii_api.config import get_settings
from torii_api.db.base import Base
import torii_api.db.models  # Populate Base.metadata with all models
from torii_api.db.engine import to_async_url


def read_sqlite_data(sqlite_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read all rows for each table in Base.metadata.sorted_tables from SQLite."""
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found at {sqlite_path}")

    sync_engine = create_sync_engine(f"sqlite:///{sqlite_path.as_posix()}")
    data: dict[str, list[dict[str, Any]]] = {}

    with sync_engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            result = conn.execute(select(table))
            rows = [dict(row._mapping) for row in result]
            data[table.name] = rows

        # Also grab alembic_version if present
        try:
            alembic_rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            data["alembic_version"] = [dict(r._mapping) for r in alembic_rows]
        except Exception:
            data["alembic_version"] = []

    return data


async def migrate(
    sqlite_path: Path,
    target_url: str,
    dry_run: bool = False,
    clean_target: bool = False,
) -> None:
    print(f"[*] Source SQLite: {sqlite_path}")
    data = read_sqlite_data(sqlite_path)

    total_rows = sum(len(rows) for rows in data.values())
    print(f"[*] Read {total_rows} total rows across {len(data)} tables from SQLite.\n")

    for tbl_name, rows in data.items():
        if rows:
            print(f"    - {tbl_name:30}: {len(rows)} rows")

    if dry_run:
        print("\n[OK] Dry-run completed successfully. No data was written to the remote database.")
        return

    async_url = to_async_url(target_url)
    if not ("postgresql" in async_url or "postgres" in async_url):
        raise ValueError(
            f"Target database URL must be a PostgreSQL database (got {target_url})."
        )

    print(f"\n[*] Connecting to target database: {target_url.split('@')[-1]} (password masked)...")
    conn_args: dict[str, Any] = {}
    if "asyncpg" in async_url:
        conn_args["statement_cache_size"] = 0
        if "sslmode=require" in target_url or "ssl=require" in target_url or "supabase" in target_url:
            conn_args["ssl"] = "require"

    target_engine = create_async_engine(
        async_url,
        connect_args=conn_args,
        pool_pre_ping=True,
    )

    async with target_engine.begin() as conn:
        # Check that tables exist in target
        inspector_tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        if not inspector_tables:
            raise RuntimeError(
                "Target database has no tables! Please run infra/supabase/schema.sql in the "
                "Supabase SQL Editor first, then run this migration script."
            )

        print("[*] Target database verified. Transferring records...")

        # If clean_target is specified, truncate tables in reverse order
        if clean_target:
            print("[*] Cleaning existing data in target database...")
            for table in reversed(Base.metadata.sorted_tables):
                if table.name in inspector_tables:
                    await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE;'))

        # Ensure any missing foreign keys in jurisdictions from historical dev data are satisfied
        existing_jids = {r["id"] for r in data.get("jurisdictions", [])}
        referenced_jids = set()
        for r in data.get("visa_categories", []):
            referenced_jids.add(r.get("jurisdiction_id"))
        for r in data.get("case_actions", []):
            referenced_jids.add(r.get("jurisdiction_id"))
        for r in data.get("cases", []):
            referenced_jids.add(r.get("jurisdiction_id"))

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        missing_jids = sorted(jid for jid in referenced_jids if jid and jid not in existing_jids)
        for missing_id in missing_jids:
            data["jurisdictions"].append({
                "id": missing_id,
                "code": f"ARCH_{missing_id}",
                "name": f"Archived Market {missing_id}",
                "is_live": False,
                "is_enabled": False,
                "created_at": now,
                "updated_at": now,
            })

        # Insert data in topological dependency order
        for table in Base.metadata.sorted_tables:
            rows = data.get(table.name, [])
            if not rows:
                continue

            if table.name not in inspector_tables:
                print(f"    [!] Skipping {table.name} (not found in target schema)")
                continue

            print(f"    [+] Migrating {len(rows):3d} rows -> {table.name}...")
            # Batch upsert or insert
            stmt = pg_insert(table).values(rows)
            # If primary keys exist, on conflict do nothing
            primary_keys = [c.name for c in table.primary_key.columns]
            if primary_keys:
                stmt = stmt.on_conflict_do_nothing(index_elements=primary_keys)

            await conn.execute(stmt)

        # Transfer alembic_version if table exists
        if "alembic_version" in inspector_tables and data.get("alembic_version"):
            for r in data["alembic_version"]:
                await conn.execute(
                    text(
                        "INSERT INTO alembic_version (version_num) "
                        "VALUES (:version_num) ON CONFLICT (version_num) DO NOTHING"
                    ),
                    {"version_num": r["version_num"]},
                )

        # Reset serial sequences for integer primary keys in PostgreSQL
        print("\n[*] Updating PostgreSQL auto-increment sequences...")
        for table in Base.metadata.sorted_tables:
            has_id = any(c.name == "id" for c in table.columns)
            if has_id and table.name in inspector_tables:
                seq_query = text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                    f"COALESCE(MAX(id), 1)) FROM \"{table.name}\";"
                )
                try:
                    await conn.execute(seq_query)
                except Exception:
                    # Some tables might not use sequences, ignore silently
                    pass

    await target_engine.dispose()
    print("\n[OK] Successfully migrated all database records to Supabase!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite database to Supabase PostgreSQL.")
    parser.add_argument("target_url", nargs="?", default=None, help="Target PostgreSQL connection string")
    parser.add_argument("--sqlite-path", default="apps/api/torii.db", help="Path to source SQLite file")
    parser.add_argument("--dry-run", action="store_true", help="Inspect local data without pushing to remote")
    parser.add_argument("--clean", action="store_true", help="Truncate target tables before inserting")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path).resolve()
    target_url = args.target_url

    if not target_url and not args.dry_run:
        settings = get_settings()
        if settings.database_url and ("postgresql" in settings.database_url or "postgres" in settings.database_url):
            target_url = settings.database_url
        else:
            print("Error: No target PostgreSQL connection string provided.")
            print("Either pass it as an argument:")
            print("    python scripts/migrate_sqlite_to_supabase.py \"postgresql://...\"")
            print("Or set TORII_DATABASE_URL in .env to your Supabase PostgreSQL URL.")
            sys.exit(1)

    asyncio.run(
        migrate(
            sqlite_path=sqlite_path,
            target_url=target_url or "",
            dry_run=args.dry_run,
            clean_target=args.clean,
        )
    )


if __name__ == "__main__":
    main()
