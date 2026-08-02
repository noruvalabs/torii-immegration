# Torii FastAPI + Next.js Shared Rules

All AI coding agents working in this repo must follow these rules.

## Core Rules

- Read nearby code, READMEs, package scripts, and existing tests before editing.
- Make the smallest complete change that solves the request; avoid drive-by refactors, renames, dependency bumps, and unrelated formatting churn.
- Follow existing helpers, components, route patterns, naming, test style, and folder boundaries.
- Search before adding a helper, component, client, formatter, config, dependency, or new pattern.
- Preserve user work. Do not revert local changes unless explicitly asked.
- Treat FastAPI as the system of record. Business rules, eligibility logic, case state, payments, audit log, and deterministic rule evaluation belong in the API, not UI-only code or model output.
- Prefer boring, proven mechanisms over clever abstractions. If control flow needs a private explanation, simplify it.
- Delete dead code introduced or exposed by the change.

## Branch And Commit Safety

- Never push directly to `main`, `develop`, or `staging`. Use a feature/fix branch and PR flow.
- Before committing, review `git diff` and ensure only intended files changed.
- Before commit, run lint, typecheck, and tests for the affected stack.
- If a gate cannot run or was already failing, report the exact command and failure.

## Repo Commands

- Root gates: `pnpm lint`, `pnpm typecheck`, `pnpm test`.
- API gates from `apps/api`: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run pytest`.
- Web gates from `apps/web`: `pnpm lint`, `pnpm typecheck`, `pnpm build`.

## Types And Contracts

- Keep strict typing. Avoid `any`, broad `dict`/`object`/`Record<string, unknown>`, bare collections, and unexplained ignores.
- Use narrow domain types: enums/literal unions for statuses, branded or `NewType` ids, and discriminated unions for variant shapes.
- Optional/null values must represent real domain states, not unfinished modeling.
- Validate at the edge, then trust the type inside the app.
- The OpenAPI schema is the API contract. Generate or derive frontend types when tooling exists; do not hand-write response mirrors.
- Separate create/update/read schemas and models; never leak storage models through API routes.
- Prefer `satisfies`, `z.infer`, `Pick`, `Omit`, and generated types over casts and copied interfaces.

## FastAPI Standards

- Keep routers thin: parse, authorize, delegate, return. Put business logic in services and persistence in repositories/models.
- Services should be framework-free async functions where possible, so APIs, workers, tests, and CLIs can share behavior.
- Use typed Pydantic request/response models, Pydantic v2, pydantic-settings, SQLAlchemy 2 async, Alembic, async HTTP clients, and structured errors consistently.
- Repositories own query shape and tenant scoping; routers should not touch ORM models directly.
- Use one settings module, one session dependency, one error shape, one pagination envelope, one HTTP client factory, and one retry policy.
- Keep migrations aligned with model changes. Generate and read Alembic migrations for schema changes.
- Avoid blocking the event loop, N+1 queries, unbounded list endpoints, hidden writes in reads, and unscoped tenant queries.
- Outbound calls need timeouts and defined failure modes. Retry only idempotent work, with backoff and a cap.
- Never log secrets, tokens, PII, raw driver errors, tracebacks, or full request bodies.

## Next.js Standards

- Use App Router conventions and existing component organization.
- Prefer Server Components for data loading; use client components only for state, effects, handlers, or browser APIs.
- Keep `"use client"` at the smallest leaf. Pass server data down as props instead of promoting a whole route to a client island.
- Use TypeScript strictly and existing UI primitives from `src/components/ui` before creating new primitives.
- Use `lucide-react` icons for icon buttons and common actions unless the project has a stricter icon seam.
- Keep API calls routed through existing backend/proxy patterns and generated clients when configured.
- Use the right owner for state: server data -> TanStack Query when client refetch/mutation is needed; URL state -> nuqs; forms -> react-hook-form + zod; local UI -> `useState`; complex shared client-only state -> Zustand only when simpler state is no longer enough.
- Do not store server data in Zustand; use TanStack Query for client-side server data that refetches, polls, caches, or mutates.
- Use react-hook-form + zod for non-trivial forms, multi-step flows, and user-entered data; validate server actions and API mutations at the boundary.
- Prefer `next/image` and `next/font` when configured. Give media stable sizes to avoid layout shift.

## Mobile UI Priority

- Design mobile-first from 360px up, then expand to tablet and desktop.
- Verify user-facing pages at narrow widths before considering them done.
- Ensure tap targets are large enough, controls are reachable, and forms remain usable on phones.
- Avoid horizontal overflow, clipped labels, overlapping text, and fixed-width layouts; prefer responsive grids, wrapping toolbar groups, and stacked mobile forms.
- Keep admin screens dense but scannable: fast scanning, predictable navigation, and repeated operational workflows over marketing-style sections.

## Useful, Optimized Work

- Optimize the common path first. Avoid waterfalls, duplicate fetches, over-fetching, unnecessary client islands, and slow query shapes.
- Add loading, empty, error, success, and disabled states where the workflow needs them.
- Keep accessibility basics intact: semantic elements, labels, focus states, keyboard behavior, and color contrast.
- Use proven packages for solved problems, but do not introduce a package for a one-liner or speculative future need.
- Prefer database constraints over duplicated application checks, SQL filtering over Python filtering, URL state over client stores, and FastAPI/Next.js built-ins over custom frameworks.
- Add abstraction on the third real use or when it removes clear complexity. Two similar call sites are often clearer than a premature generic wrapper.
- Cache only with a measured reason or clear product need. Make invalidation explicit.

## Testing And Response

- A behavior change needs tests; a bug fix needs the test that would have caught it.
- Cover important unhappy paths, permissions, validation, duplicate/conflict cases, outbound failures, and primary user journeys.
- Backend changes should include service/repository tests where logic lives and API tests where behavior crosses HTTP boundaries.
- Frontend changes should test user-observable behavior by role/label. Use Playwright for critical flows that must not break.
- Do not use live network in tests. Mock at the HTTP/fetch transport boundary.
- In responses, state what changed, how it was verified, important file paths, skipped checks, risks, and assumptions.

## Product Context

- Torii is a guided form-preparation platform, **not** legal advice — the UPL line in
  `docs/specs/01_domain.md` is binding.
- Primary user is a **foreign resident in Japan**. Japan filings are domestic/self-filed;
  US filings are consular via the embassy or consulate in Japan.
- Read order: `docs/specs/00_overview.md` → `01_domain.md` → `02_requirements.md` →
  `docs/plan/00_applicant_v1.md` for sequencing.
- **NF-1**: rule-governed output is deterministic, never model-inferred.
  **NF-2**: nothing user-facing ships without an official-source citation.
- Jurisdiction content lives in `docs/jurisdictions/*.yml` (loaded by seed into the API DB),
  not as long-lived Python dict constants.
- Do not automate government portals (`docs/decisions/0004-no-portal-automation.md` when present).
