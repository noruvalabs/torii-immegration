# web

Torii's Next.js front end — the applicant app and the **ops/admin back office**, off the same
FastAPI system of record. App Router, TypeScript, Tailwind v4, light/dark, mobile-first.

> The admin dashboard shell is structured after the reference monorepo's back office, but the
> content is Torii's immigration domain — a **case pipeline**, jurisdictions, a knowledge base,
> and a review queue. There is deliberately **no commerce**.

## Run

```bash
pnpm install
pnpm dev            # http://localhost:3000  (landing) · /admin (back office)
```

The admin talks to the API. Browser calls to `/backend/*` are rewritten to the FastAPI service
(default `http://localhost:8000`, override with `API_PROXY_TARGET`). Start the API first
(`cd ../api && uv run uvicorn torii_api.main:app --reload`) to see live jurisdiction data on the
dashboard and manage jurisdictions end to end.

## Layout

```
src/app/
  page.tsx              applicant-facing landing (guided form prep — not legal advice)
  admin/
    layout.tsx          sidebar + header shell
    page.tsx            dashboard (live API status + spec-mapped KPI cards)
    jurisdictions/      interactive: list + create against the live API
    cases/  review-queue/  employers/  forms/  knowledge-base/
    staff/  reports/  settings/        section shells mapped to their user stories
  api/health/route.ts   container health probe
src/components/
  admin/                sidebar · header · nav config · theme toggle · section placeholder
  ui/                   card · badge · button (self-contained primitives)
```

## Gates

```bash
pnpm typecheck        # tsc --noEmit
pnpm lint             # eslint (next config)
pnpm build            # production build (standalone output for Docker)
```

## Configuration

| Variable | Where | Purpose |
|---|---|---|
| `API_PROXY_TARGET` | dev server | target for the `/backend/*` → API rewrite (default `http://localhost:8000`) |
| `API_INTERNAL_BASE_URL` | server (RSC) | API base for server-side dashboard fetches (default `http://localhost:8000`) |
