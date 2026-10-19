# Torii ⛩️

**Guided visa preparation & immigration concierge platform** — simplifying complex international visa applications.

### Our Core Mission
Navigating official government immigration websites is notoriously complex, slow, and error-prone. Users face confusing portals, rigid form requirements, and payment gateways that reject local cards. Torii eliminates this entire burden:

1. **Full-Service Government Portal Submission & Fee Payment** *(When a country has an online portal & digital fee)*
   - **One-Stop Data Intake**: The user provides their information once on Torii's clean, modern interface. Profile and passport data are securely saved and can be reused for future trips and family members without re-typing.
   - **No Portal Hassle**: The user never has to navigate messy foreign government websites or foreign currency payment roadblocks.
   - **All-in-One Local Payment**: The user pays all fees (Torii service fee + government fee) in a single transaction to Torii using familiar local payment methods.
   - **Staff Concierge Fulfillment**: Torii's operations staff logs into the official government website, enters the applicant's verified data, pays the government visa/portal fee, and downloads the official registration barcodes and payment receipts.
   - **Complete Delivery**: We send the user their confirmed filing invoice, appointment slips, and visa documents directly to their dashboard.

2. **Official Form Preparation & In-Person Dossier Kit** *(When a country does not have online portal payment and requires in-person submission or paper forms, e.g. Japan)*
   - **Affordable Service Charge**: The user pays only a nominal Torii service charge.
   - **Flawless Official Documentation**: Torii's platform and team generate the exact official typewritten government forms (e.g. Japan's 2-page MOFA form, day-by-day Schedule of Stay itinerary, and formal consular cover letter).
   - **Submission Ready**: If an online submission channel exists, our team submits it directly. Otherwise, we deliver a flawless, print-ready PDF dossier to the user so they can submit it in person at VFS/IVAC/Embassy, paying the consular fee only upon approval.

In short, **Torii takes over all the complex online work** so travelers never get stuck or confused.

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
pnpm install    # once — installs the web deps and registers apps/api and apps/ai with turbo
(cd apps/api && uv run alembic upgrade head && uv run torii-seed)
pnpm dev        # runs the API (8000), AI service (8001), and web app (3000) together, prefixed logs
# → http://localhost:3000            applicant landing
# → http://localhost:3000/admin      back office (talks live to the API)
# → http://localhost:8000/health · /docs   ·   http://localhost:8000/v1/jurisdictions
# → http://localhost:8001/health · /docs   (AI assistant & agentic research)
```

`pnpm dev` is `turbo run dev`, which runs each app's own `dev` script in parallel: `apps/web`
runs `next dev`; `apps/api` runs FastAPI on port 8000; `apps/ai` runs the AI/research engine on port 8001.

Run just one service with `pnpm --filter web dev`, `pnpm --filter api dev`, or `pnpm --filter ai dev`.
The seed command is idempotent and creates local demo users plus all bundled jurisdiction content.

### Optional local credentials

No API keys are required for the local demo: SQLite, seeded content, fake AI/search clients,
mock payments, and logged email links keep the main flow usable. For live AI answers, research,
and document OCR, set `TORII_AI_GROQ_API_KEY` and `TORII_AI_TAVILY_API_KEY` in the root `.env`.
SMTP settings are only needed to deliver real verification/reset emails. The current Google button
is a local social-login mock, not a verified Google OAuth integration.

### Everything, together (Postgres + Redis + nginx)

```bash
cp infra/.env.example infra/compose/.env   # then edit
docker compose -f infra/compose/docker-compose.yml up -d --wait
```

## Toolchain

- **Python** via [uv](https://docs.astral.sh/uv/) — `apps/api` is a standalone uv project.
- **Node 22+** via pnpm (provisioned by corepack from the `packageManager` pin). Turborepo
  orchestrates the JS/TS tasks: `pnpm build`, `pnpm lint`, `pnpm typecheck`, `pnpm test`.
