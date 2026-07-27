# Torii FastAPI + Next.js Consistency Guide

Use this file as the instruction set for Codex CLI working in this repository. Keep changes consistent with the existing repo before adding new patterns.

## Core Rules

- Read the nearby code, README, and package scripts before editing.
- Make the smallest complete change that solves the request.
- Prefer existing helpers, components, route patterns, naming, and test style.
- Keep unrelated refactors out of feature or bugfix changes.
- Preserve user work. Do not revert local changes unless explicitly asked.
- Treat the FastAPI app as the system of record. Business rules, eligibility logic, case state, payments, audit log, and deterministic rule evaluation belong in the API, not in UI-only code or model output.
- Add or update tests when behavior changes.
- Before committing, always run lint and tests. Also run type checks when available.

## Repo Commands

From the repo root:

```bash
pnpm lint
pnpm typecheck
pnpm test
```

API-specific gates from `apps/api`:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

Web-specific gates from `apps/web`:

```bash
pnpm lint
pnpm typecheck
pnpm build
```

If a command cannot run because dependencies, services, or environment variables are missing, report the exact command, the failure, and what is needed to rerun it.

## FastAPI Standards

- Keep route handlers thin. Put reusable business behavior in services or domain modules.
- Use typed Pydantic request and response models for API boundaries.
- Use SQLAlchemy async patterns already present in the codebase.
- Keep migrations aligned with model changes. Generate Alembic migrations for schema changes.
- Avoid hidden database writes in read endpoints.
- Keep auth, permissions, audit, and validation explicit.
- Return stable, documented response shapes. Do not break existing clients without updating callers and tests.
- Prefer deterministic logic and stored state over LLM interpretation for immigration workflows.

## Next.js Standards

- Use App Router conventions and existing component organization.
- Prefer server components for data loading unless client interactivity is required.
- Keep client components focused on state, events, and browser-only behavior.
- Use TypeScript strictly. Avoid `any` unless there is a clear boundary and a comment explains why.
- Use existing UI primitives from `src/components/ui` before creating new primitives.
- Use `lucide-react` icons for icon buttons and common actions.
- Keep API calls routed through existing backend/proxy patterns when applicable.
- Do not duplicate API contracts manually when a shared type or schema pattern exists.

## Mobile UI Priority

- Design mobile-first, then expand to tablet and desktop.
- Verify every user-facing page at narrow widths before considering it done.
- Ensure tap targets are large enough, controls are reachable, and forms remain usable on phones.
- Avoid horizontal overflow, clipped labels, overlapping text, and fixed-width layouts.
- Prefer responsive grids, wrapping toolbar groups, and stacked form layouts on mobile.
- Keep admin screens dense but scannable: prioritize fast scanning, predictable navigation, and repeated operational workflows over marketing-style sections.

## Useful, Optimized Work

- Optimize for the path users take most often, not the rarest edge path.
- Keep pages and endpoints fast by avoiding unnecessary waterfalls, duplicate fetches, and over-fetching.
- Add loading, empty, error, and success states where a real user workflow needs them.
- Keep accessibility basics intact: semantic elements, labels, focus states, keyboard behavior, and color contrast.
- Prefer clear domain language over generic placeholders.
- Remove dead code introduced by the change.

## Commit Checklist

Before any commit:

1. Review `git diff` and ensure only intended files changed.
2. Run lint, typecheck, and tests:
   ```bash
   pnpm lint
   pnpm typecheck
   pnpm test
   ```
3. For API-heavy changes, also run the API-specific gates.
4. For web-heavy changes, also run `pnpm build` in `apps/web`.
5. Mention any skipped or failing verification clearly in the final response or commit notes.

## Response Style

- Be concise and practical.
- State what changed and how it was verified.
- Include file paths for important edits.
- Call out risks, assumptions, or skipped checks directly.
