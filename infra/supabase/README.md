# Supabase

Torii's system of record on Supabase: what to load, how to connect, and what to change in the
application so it behaves correctly against a pooled, managed Postgres.

`schema.sql` is **generated**. Do not hand-edit it — regenerate (below) so it can never drift
from Alembic, which remains the source of truth.

## Loading the schema

1. Enable `vector` on the project: **Database → Extensions → `vector`**. Supabase installs it
   into the `extensions` schema, which is what `schema.sql` expects.
2. Open the **SQL Editor**, paste the whole of `schema.sql`, run it.
3. Confirm: 22 tables in `public`, and `select * from alembic_version` returns one row, `0019`.

That last row is load-bearing. `pg_dump --schema-only` emits the `alembic_version` table but
not its row, because the row is data. An unstamped database makes the API conclude no
migrations have been applied and try to replay all 19 over a schema that already exists —
failing on the first `CREATE TABLE`. The generator appends the stamp for exactly this reason.

## Connecting the API

Supabase gives two connection strings, and Torii needs both for different jobs.

| Use | Port | Why |
| --- | --- | --- |
| The running app | **6543** (Supavisor, transaction mode) | Survives many short-lived connections, which is what an autoscaling Cloud Run service produces |
| Alembic migrations | **5432** (direct) | Transaction pooling does not support the session-level state DDL relies on |

Two settings are not optional with asyncpg behind the pooler:

```python
# apps/api/src/torii_api/db/engine.py
create_async_engine(
    url,
    connect_args={"statement_cache_size": 0},  # required: Supavisor reuses backends, so
                                               # asyncpg's prepared statements collide
                                               # ("prepared statement _pg_N already exists")
    pool_size=3, max_overflow=2,               # per INSTANCE, not per deployment
)
```

The pool sizes matter more than they look. The current values (10 + 5) were tuned for a single
long-lived container on a 1 GB VM. Under Cloud Run each instance opens its own pool, so ten
instances at 10+5 is 150 connections — well past what a small Supabase project allows. Size the
pool for one instance and let the pooler absorb the fan-out.

## Application changes this migration requires

Three settings that are correct on a single VM become wrong the moment the API autoscales.

- **`TORII_MIGRATE_ON_STARTUP=false`.** Today every API process runs `alembic upgrade head` at
  boot. That is fine for one container and a race for many: several cold-starting instances
  would migrate the system of record concurrently. Migrations move to a deploy step (a Cloud
  Run Job, or a Cloud Build step) against the **direct** 5432 connection.
- **`TORII_SEED_ON_STARTUP=false`.** Same reasoning, plus it re-reads every jurisdiction pack
  on each cold start. Seeding becomes a deliberate step, not a side effect of scaling up.
- **Document storage must leave the local filesystem.** `services/wallet.py` writes uploads to
  the relative path `data/wallet_storage`, and nothing mounts it. On a VM that loses every
  uploaded passport and contract on each deploy. On Cloud Run it is worse: the filesystem is
  in-memory, so uploads consume the instance's memory budget *and* vanish when the instance
  recycles. This has to move to Supabase Storage (or GCS) **before** any serverless cutover,
  not after.

## Regenerating `schema.sql`

Run the migrations against a throwaway database and dump the result — never write the SQL by
hand. Against any host with the stack running:

```bash
docker exec <postgres> sh -c 'psql -U $POSTGRES_USER -d postgres \
  -c "DROP DATABASE IF EXISTS torii_schema_gen;" -c "CREATE DATABASE torii_schema_gen;"'
docker exec <postgres> sh -c 'psql -U $POSTGRES_USER -d torii_schema_gen \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"'
docker exec <api> sh -c 'cd /app &&
  TORII_DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/torii_schema_gen" \
  alembic upgrade head'
docker exec <postgres> sh -c 'pg_dump -U $POSTGRES_USER -d torii_schema_gen \
  --schema-only --no-owner --no-privileges --no-comments'
```

Then apply the three Supabase adjustments the header of `schema.sql` lists, append the
`alembic_version` stamp, and **drop the throwaway database**.

Verify the result the way the committed file was verified — load it into an empty database and
confirm the API considers it current:

```bash
alembic upgrade head   # must exit 0 with no output; anything else means the stamp is wrong
```
