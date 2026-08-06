# Live research-driven case flow — implementation tracker

> **Purpose of this doc.** Durable context for resuming this feature after context loss.
> Product truth: `docs/specs/`; sequencing: `docs/plan/00_applicant_v1.md`. This doc is the
> working log for the "search online for every case" feature.

## Goal (user words)
Automate the whole process for an applicant moving country→country (e.g. a Bangladeshi citizen
legally in Japan applying for a UK Standard Visitor visa). When a case starts, the system must
**search the web live** for that specific case (origin + residence + destination + purpose),
produce the required documents, questions, forms, and a final organized packet the applicant can
take to the embassy/portal and fill/submit easily. Common/identity info is saved once and reused.
The current flow is "static" (seeded YAML packs) and must become research-driven per case.

## Decisions (confirmed with founder 2026-08-03)
1. **General pipeline for ANY country pair** (per-destination official-domain map), validated
   end-to-end with BD-in-Japan → UK tourist.
2. **Cache research per scope** with ~7-day expiry; next same-scope case is instant. A
   re-research action forces fresh.
3. **Results usable immediately** once citation-gated (NF-2) — no ops human review. Global live
   rules are NEVER mutated → NF-9 human-review gate does not apply.
4. **Wizard offers research-enabled destinations** (UK + origin/residence step). A scope is
   selectable if a live pack OR research is available.

## How the system works today (from code, verified)
- Pipeline: `POST /v1/cases/scope` (`apps/api/src/torii_api/api/cases.py:223`) → intake →
  eligibility → checklist → documents → forms → review → packet → submit, driven by
  `services/guidance.py:compute_guidance`. All content comes from DB rows seeded from
  `docs/jurisdictions/*.yml` via `management/seed.py`.
- Content tables: `intake_definitions`, `eligibility_rule_sets`, `document_requirement_sets`,
  `form_templates` (all `is_live`). `_def_flags` (`cases.py:389`), `_scope_definition`
  (`api/case_workflow.py:125`), `_case_guidance` (`cases.py:444`).
- Guidance phases (`services/guidance.py:14`): intake|eligibility|checklist|forms|review|packet|
  done|blocked. No `research` phase today. `missing_live_workflow_definitions` blocked branch at
  `guidance.py:72`.
- Live-search machinery ALREADY EXISTS (currently ops-only, daily batch, JP/US only):
  - `apps/ai/src/torii_ai/services/ops_scraper.py` — Tavily discovers official pages → scrape →
    Groq LLM extracts `eligibility_rules/document_requirements/intake_questions/form_templates`,
    each with a citation. `JURISDICTION_QUERIES` hardcoded JP/US only (`:29`). Extract prompt `:48`.
  - `apps/ai/src/torii_ai/api/ops.py:82` `POST /ai/ops/scrape` (`ScrapeRequest` at `:31`).
  - API worker `apps/api/src/torii_api/worker/scheduler.py:87` calls it daily; gates via
    `services/ops_ingest.py:validated_for_promote` (every item needs `citation.url` http).
  - `apps/ai/src/torii_ai/tools/tavily.py:42` `search()` — domains settings-only (`:47`).
- Web: scope wizard `apps/web/src/app/(app)/scope/page.tsx` (geo codes, no origin/residence step);
  case page `apps/web/src/app/(app)/cases/[id]/page.tsx` (thin guidance-phase switch, `:59`);
  step components `apps/web/src/components/applicant/steps/`; `phaseToStep` in `steps/types.ts`;
  `scopeCase` in `apps/web/src/lib/api/cases.ts:180`; geo in `apps/web/src/lib/api/geo.ts`.
  Geo destination/visa/application-type lists live in `apps/api/src/torii_api/services/geolocation.py`.
- Binding constraints (docs/specs/02_requirements.md:544): **NF-1** rule-governed output is
  deterministic, never model-inferred (LLM proposes, engine consumes); **NF-2** nothing user-facing
  ships without an official-source citation (uncited → dropped). No-portal-automation (guided-fill
  only, ADR-0004 substance in `docs/plan/00_applicant_v1.md` §M3).

## Design (one line)
Add a **Research phase**: when a case's scope has no live content pack, the system researches that
exact case live, produces a citation-gated, cached snapshot (`ScopeResearch`), and feeds it into the
same deterministic engine — intake → eligibility → checklist → forms (guided-fill for online) → review
→ packet.

## Implementation steps
### R1 — Foundation (apps/api + apps/ai) ✅ DONE (2026-08-03)
- Models: new `ScopeResearch` table (scope + origin_country + residence_country, status
  queued|running|completed|failed, payload JSON, source_pages, error, researched_at, expires_at,
  unique scope+origin+residence). `Case` += `origin_country, residence_country, research_id`.
  `VisaCategory`/`CaseAction` += `research_enabled`. Alembic `0011_scope_research`.
- Scope: accept origin/residence; accept `research_enabled` scopes; enqueue outbox
  `case.research.queued` when no live defs and no fresh cache (`cases.py:223`).
- Guidance: add `research` phase (`guidance.py:14`), `research_status` input; replace blocked branch
  (`:72`) with research running → research phase; failed → `research_failed` blocked + escalation;
  present → proceed. `next_status_for_phase` + `_def_flags` fallback to `ScopeResearch.payload`.
- Worker: arq task `run_case_research` consumes `case.research.queued` →
  `POST /ai/ops/scrape` (+origin/residence, `return_payload:true`) →
  `validated_for_promote` → write `ScopeResearch` (completed/failed, expires 7d).
- AI: generalized `ops_scraper.py` — per-destination official-domain map (`OFFICIAL_DOMAINS`, incl.
  gov.uk/homeoffice.gov.uk; keeps isa.go.jp/moj.go.jp) + `build_queries(destination, visa, action,
  origin, residence)`; origin/residence context in extraction prompt. `tavily.py` `search()`
  accepts per-request `domains`. `api/ops.py` `ScrapeRequest` += `origin_country`/`residence_country`.
- Tests added: `test_scope_research.py` (7), `test_guidance_research.py` (7),
  `test_ops_scraper_general.py` (7). API suite: 70 passed. AI suite: 19 passed + 1 pre-existing
  failure (see below). `alembic upgrade head` + downgrade/upgrade round-trip verified on dev sqlite.
- Also fixed (pre-existing bugs surfaced by enabling test collection):
  - `apps/ai/api/ops.py` imported `GroqClient` (renamed `GroqChatClient`).
  - `apps/api/api/cases.py:738` referenced undefined `definition`; missing `find_research` import.
  - scope endpoint unknown-jurisdiction status restored to 400 (existing contract).
- **Known pre-existing, left untouched (out of R1 scope):** AI test
  `test_ocr_extract_endpoint` fails 404 — OCR router prefix is `/ocr` but test posts to `/ai/ocr`
  (`apps/ai/src/torii_ai/api/ocr.py:14`). `python-multipart` is required by the `/extract-file`
  form endpoint but absent from `apps/ai/pyproject.toml` (installed in venv only to unblock tests).
  ~80 pre-existing ruff E501/F401 in untouched files (`gov_scraper.py`, `services/ocr.py`,
  `scrape_gov.py`, `0007_applicant_core.py`, `test_case_delete.py`).

### R2 — UI (apps/web)
- Wizard: origin/nationality step; send origin/residence to `scopeCase`.
- New `ResearchStep` polling `GET /cases/{id}/guidance`; map `research` in `phaseToStep`.
- FormsStep → guided-fill for `is_online` forms (per-field answer + copy + official term +
  plain-language + citation). PacketStep → include source_pages + answers-at-a-glance.
### R3 — Content/seed + E2E
- `docs/jurisdictions/uk/_jurisdiction.yml` + `uk/tourist.new_application.yml`
  (`research_enabled:true, is_live:false`). Seed UK + tourist + new_application. Add UK to
  `services/geolocation.py` lists.
- E2E: BD-in-Japan → UK tourist reaches intake with researched questions; every checklist item
  carries a citation.

## Tests
`test_scope_research.py` (enqueue / citation gate / stale cache re-research / failed → blocked /
same-scope reuse), `test_guidance_research.py`, `test_ops_scraper_general.py` (query builder +
domains), extend `test_content_packs.py`.

## Risks
- JS-heavy gov.uk pages scrape poorly → items dropped by citation gate. Mitigate: `low_coverage`
  status + escalation alongside partial results.
- Latency 30–90s → async + polling. Cost → 7-day per-scope cache.
- NF-1 preserved: research is content; engine stays deterministic; reuse `validated_for_promote`.
- No portal automation: guided-fill only.

## Verification
`pnpm --filter api test` after R1; `pnpm dev` + walk BD→UK case after R3; `pnpm lint`/`typecheck`.
