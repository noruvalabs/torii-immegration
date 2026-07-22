# ADR 0001 — Monorepo scaffold: FastAPI + Next.js, dual-DB, arq scheduler

**Date:** 2026-07-22 · **Status:** accepted

## Context

We are standing up the Torii platform foundation. The product spec ([`docs/specs/`](../specs/))
calls for a FastAPI system of record, a Next.js applicant app + ops/admin back office, and
background work (renewal reminders, a government-change monitor, an outbox). The repository shape
follows a reference monorepo (turbo + pnpm workspace, standalone `uv` Python services, per-app
Dockerfiles behind one nginx edge). The reference's API is .NET; ours is FastAPI.

## Decisions

1. **Monorepo, same shape as the reference.** `apps/` + `packages/` + `infra/` + `docs/`, turbo
   over a pnpm workspace for the JS/TS side. `apps/api` is a standalone `uv` project and is *not*
   a workspace member (no `package.json`) — Python tooling stays independent of Node.

2. **`apps/api` is the system of record (FastAPI + SQLAlchemy 2 async).** Deterministic
   rule-governed truth lives here (NF-1). Rewritten from the reference's .NET API; conventions
   (config via `BaseSettings`, structlog JSON logs, Scalar docs, programmatic Alembic) mirror the
   reference's Python `assistant` service so the two feel like one codebase.

3. **One database URL, two engines.** `TORII_DATABASE_URL` selects the engine: **SQLite**
   (`aiosqlite`) by default so the API runs with zero infrastructure, **Postgres** (`asyncpg`)
   in deployment. The async driver is derived automatically (`db/engine.to_async_url`); no model
   or query code is dialect-specific. Alembic's env enables SQLite batch mode so ALTER-heavy
   migrations work on both. *Verified: `alembic upgrade head` + full CRUD on both engines.*

4. **arq (Redis) for background work.** Chosen over APScheduler (no durability / single-process)
   and Celery (heavier, thread/prefork model that fits async poorly). arq gives one tool for both
   the **cron schedule** (outbox drain every 10s, renewal reminders daily, change monitor hourly)
   and an **ad-hoc task queue**, natively async. The API connects to Redis **best-effort** with a
   clamped retry so a Redis outage never blocks startup or the request path; durable, must-not-lose
   work goes through the transactional `outbox_events` table, not the queue.

5. **Admin dashboard reframed, not ported.** The Next.js back-office *shell* (sidebar + header +
   section layout, light/dark) follows the reference's admin structure, but every surface is
   Torii's immigration domain — a case pipeline, jurisdictions, a knowledge base, a review queue —
   and each section links to the user stories it will satisfy. **No commerce.**

6. **The reference stays out of the repo.** `.reference/` is gitignored — architectural reference
   only, never shipped.

## Consequences

- A developer can clone and run the API with `uv sync && alembic upgrade head && uvicorn …` — no
  database or Redis required. The full stack (Postgres + Redis + nginx) comes up with one
  `docker compose up`.
- `apps/ai` (the model-facing RAG/intake/citation service in the architecture doc) is **not yet
  scaffolded** — it is the next service, and will follow `apps/api`'s conventions.
- Swapping arq's Redis for a managed queue later touches only `worker/` and `db.session`-adjacent
  enqueue calls, not domain code.
