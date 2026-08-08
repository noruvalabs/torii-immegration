# Torii ⛩️

**Guided form-preparation platform for immigration** — a "TurboTax for visas". Torii walks a
person through renewing a visa, changing status, or filing a new application: conversational
intake, an eligibility read, a personalized document checklist, auto-filled government forms, a
final consistency check, and post-submission tracking with renewal reminders. Every instruction
links to the official government source it came from.

> "Torii" (⛩️ — the gate one passes through to enter) is a working codename. Product truth lives
> in [`docs/specs/`](docs/specs/); read [`00_overview.md`](docs/specs/00_overview.md) first.

## Stack

- **API** (`apps/api`) — FastAPI (Python 3.13) · SQLAlchemy 2 async · Alembic · the system of
  record: users, cases, jurisdictions, rules, forms, documents, payments, audit.
- **Web** (`apps/web`) — Next.js (App Router, TS) · Tailwind — applicant app + the ops/admin
  back office (multilingual, mobile-first).
- **Background** — [arq](https://arq-docs.helpmanual.io/) (Redis) worker + cron for the outbox
  poller, renewal reminders, and the government-change monitor.
- **Data** — PostgreSQL 17 + pgvector in production; **SQLite** for zero-setup local dev. The API
  auto-selects the async driver from `TORII_DATABASE_URL` — no code change to switch.

## Repository layout

```
apps/api/     FastAPI — system of record (SQLAlchemy async, Alembic, arq worker/scheduler)
apps/ai/      FastAPI — grounded assistant (Groq + Tavily), citations, guardrails
apps/web/     Next.js — applicant app + ops/admin back office
packages/     shared types / generated API client (scaffolded in a later PR)
infra/        docker-compose, nginx, env templates
docs/         product specs (docs/specs) + architecture decisions (docs/decisions)
              + sequencing (docs/plan) + jurisdiction content packs (docs/jurisdictions)
```

`apps/ai` — model-facing service (assistant chat, citations, guardrails; RAG/OCR later). See
[`apps/ai/README.md`](apps/ai/README.md) and [`docs/specs/03_architecture.md`](docs/specs/03_architecture.md).

## Quick start

### Run everything with one command (zero infra — SQLite)

```bash
cp .env.example .env   # one file for apps/api, apps/ai, and apps/web — fill in secrets
pnpm install    # once — installs the web deps and registers apps/api with turbo
pnpm dev        # runs the API (uv) and the web app (next dev) together, prefixed logs
# → http://localhost:3000            applicant landing
# → http://localhost:3000/admin      back office (talks live to the API)
# → http://localhost:8000/health · /docs   ·   http://localhost:8000/v1/jurisdictions
```

`pnpm dev` is `turbo run dev`, which runs each app's own `dev` script in parallel: `apps/web`
runs `next dev`; `apps/api`'s wraps `uv run alembic upgrade head && uv run uvicorn --reload`
(Alembic auto-applies on every start — safe to re-run, so the schema is always current). `uv`
manages its own `.venv` on first run, so no separate Python install step is needed.

Run just one side with `pnpm --filter web dev` or `pnpm --filter api dev`.

`apps/ai` isn't part of the pnpm workspace (no `package.json`, standalone `uv` project like
`apps/api`) and neither it nor the arq worker/Redis are started by `pnpm dev` — start them
separately for anything that needs live research or the assistant (see `apps/ai/README.md`
and "Background worker" in `apps/api/README.md`), or they'll silently never run.

### Everything, together (Postgres + Redis + nginx)

```bash
cp infra/.env.example infra/compose/.env   # then edit
docker compose -f infra/compose/docker-compose.yml up -d --wait
```

## Toolchain

- **Python** via [uv](https://docs.astral.sh/uv/) — `apps/api` is a standalone uv project.
- **Node 22+** via pnpm (provisioned by corepack from the `packageManager` pin). Turborepo
  orchestrates the JS/TS tasks: `pnpm build`, `pnpm lint`, `pnpm typecheck`, `pnpm test`.
