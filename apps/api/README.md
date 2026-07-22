# torii-api

Torii's **system of record** (FastAPI, Python 3.13). Users and accounts, jurisdictions and
their visa/eligibility/document rules, the canonical case pipeline, forms and versioned field
mappings, the document vault, payments, and the audit log. Rule evaluation is deterministic and
lives here, never in a model ([`docs/specs/03_architecture.md`](../../docs/specs/03_architecture.md), NF-1).

Standalone [uv](https://docs.astral.sh/uv/) project (not part of the pnpm workspace).

## Run

```bash
uv sync                                     # create .venv from the lockfile
uv run alembic upgrade head                 # apply the schema (creates ./torii.db on SQLite)
uv run uvicorn torii_api.main:app --reload  # API on :8000
#   GET /health   ·   Scalar docs at /docs   ·   GET /v1/jurisdictions
```

Seed one jurisdiction to see the DB seam end to end:

```bash
curl -s localhost:8000/v1/jurisdictions -H 'content-type: application/json' \
  -d '{"code":"JP","name":"Japan","is_live":true}'
curl -s localhost:8000/v1/jurisdictions
```

## Database — SQLite or Postgres, one URL

The default is a local **SQLite** file (`./torii.db`) so the API runs with zero infrastructure.
Point `TORII_DATABASE_URL` at Postgres to switch — the async driver (`aiosqlite` / `asyncpg`)
is derived automatically, no code change:

```bash
export TORII_DATABASE_URL=postgresql://torii:torii@localhost:5432/torii
uv run alembic upgrade head
```

## Background worker (arq + Redis)

Cron schedule (outbox drain every 10s, renewal reminders daily 08:00, change monitor hourly)
plus an ad-hoc task queue. Run it next to the API; it needs Redis:

```bash
docker run --rm -p 6379:6379 redis:7-alpine     # a local Redis for dev
uv run arq torii_api.worker.scheduler.WorkerSettings
```

The API connects to the queue **best-effort** — if Redis is down, enqueue no-ops with a warning
and the request path is unaffected. Work that must not be lost goes through the transactional
`outbox_events` table (drained by the worker), not the queue.

## Migrations

```bash
uv run alembic revision -m "add X" --autogenerate   # generate from model changes
uv run alembic upgrade head                          # apply
uv run alembic downgrade -1                           # roll back one
```

`env.py` enables SQLite batch mode automatically, so ALTER-heavy migrations work on SQLite too.

## Configuration (`TORII_` env prefix)

| Variable | Default | Purpose |
|---|---|---|
| `TORII_DATABASE_URL` | `sqlite:///./torii.db` | system-of-record DB; Postgres URL switches engines |
| `TORII_MIGRATE_ON_STARTUP` | `false` | run Alembic migrations at boot |
| `TORII_REDIS_URL` | `redis://localhost:6379/0` | arq queue + cron broker |
| `TORII_OUTBOX_POLL_INTERVAL_SECONDS` | `10` | outbox drain cadence |
| `TORII_RENEWAL_REMINDER_LEAD_DAYS` | `30` | lead time before a renewal date to remind (US-19) |
| `TORII_DOCS_ENABLED` | `true` | serve Scalar docs + `/openapi.json` |
| `TORII_LOG_LEVEL` | `INFO` | structlog level |

## Gates

```bash
uv run ruff check . && uv run ruff format --check .   # lint + format
uv run pyright                                        # types (standard mode)
uv run pytest                                         # tests (throwaway in-memory SQLite)
```
