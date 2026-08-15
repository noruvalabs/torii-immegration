# Corridor-aware end-to-end visa flow — proven on Bangladesh → Japan (tourist)

> **Implementation tracker.** Durable context for resuming this feature after context loss.
> Product truth: `docs/specs/`; sequencing: `docs/plan/00_applicant_v1.md`. This is the working
> log for corridor admissibility + deep research + correspondence, proven on BD→JP tourist.
> Branch: `feat/corridor-bd-jp` (off `feat/rules-corpus`).

## Goal (user words)

Serve the *opposite* direction from today's assumption: a Bangladeshi national living in
Bangladesh applying for a Japan short-stay/tourist visa from Dhaka — end to end, so they pay
Torii instead of a lawyer or visa agent. Built **corridor-generic**
`(nationality, residence) → (destination, purpose)` from the start so later corridors (e.g.
UK → US) reuse the same tables and endpoints; BD→JP is the first proof, not a special case.

The chain, in the user's order: *can this person even go and where do they file* → *every
question the filing needs* → *eligibility* → *documents* → *forms filled* → *letters and emails*
→ *assembled packet with how/where/when to submit*.

## Decisions (confirmed with founder 2026-08-15)

1. Cover the **full chain** in this effort, not a slice.
2. Build **both** a hand-authored golden BD→JP pack **and** the research pipeline that must
   reproduce it — the pack is the quality bar and the test fixture for "dynamic == as good as
   hand-authored." **Superseded 2026-08-15, see Decisions §2 below** — the golden pack becomes an
   optional later regression fixture, not a blocking milestone.
3. When a corridor's official route requires a third party (accredited agency, VAC, sponsor),
   **prepare everything and hand off** — never block the case.
4. Letters/emails are **full LLM drafts, applicant-edited** — not fixed templates, not
   auto-sent.

Binding constraints, unchanged: **NF-1** rule-governed output is deterministic, never
model-inferred. **NF-2** nothing user-facing ships without an official-source citation.
No portal automation — guided-fill only.

## Decisions §2 — pivot to fully agentic, per-stage research (confirmed 2026-08-15)

After M0, manual verification showed the actual felt problem: different visa types/countries
were still surfacing the **same** questions and documents. Root cause confirmed in code — content
resolution is pack-first (`content_packs.py` → seeded DB rows), and most scope combinations fall
through to a generic 8-question static definition (`GENERIC_QUESTIONS` in `seed.py`) rather than
anything scope-specific. Founder decision: **stop resolving from YAML/DB packs in the request
path, for every scope, effective now** — not just for scopes lacking a pack. Every case, every
stage, gets live LLM + web-search research. Two follow-up decisions, each with a stated default:

1. **Universal, not fallback-only.** Live agentic research is the path for *every* case,
   including scopes that already have a working seeded pack (e.g. JP work-visa renewal). Packs
   stay on disk as a reference/fallback if a research call fails outright — they are not deleted,
   just no longer read at request time.
2. **Per-stage, sequential, not one upfront pass.** Each pipeline stage — intake, eligibility,
   documents (checklist), forms — runs its **own** fresh search + LLM extraction, informed by
   everything learned in prior stages (the applicant's actual answers, the eligibility result,
   etc.), rather than one research call producing everything before intake starts. Slower and
   more LLM/search calls per case; this is what makes each stage feel like an agent actually
   working *this* case instead of a lookup.

**How this stays inside NF-1 (reconciled, not waived).** "Use an LLM to validate all info" is
implemented as two distinct things, not one: the LLM+search step **discovers** candidate content
for a stage — a citation-backed eligibility rule, a document requirement, a form field mapping —
exactly as `ops_scraper.py` already does for `ScopeResearch`. The **existing deterministic
functions** (`services/eligibility.py:evaluate_eligibility`, `services/forms.py:fill_form`, the
checklist visibility logic) then evaluate the applicant's actual answers against that
LLM-discovered content, unchanged. The engine never adopts an LLM's verdict on whether a specific
applicant passes a rule — only what the rule *is*, cited to an official source. This is the same
boundary the architecture doc already draws between `apps/ai` (proposes) and `apps/api` (decides);
it now applies per-stage instead of once per scope.

**What this supersedes:** the M1 (`CorridorProfile`) design below is kept but reframed as **stage
zero** (`admissibility`) of the same per-stage engine, run before a case exists (keyed by scope +
nationality + residence, no `case_id` yet). M2 (pack selector + golden BD→JP pack) is deferred —
selectors solve "pick the right static pack," which stops being the mechanism. M3 (aspect-sharded
research) is superseded by the per-stage engine directly: each stage *is* an aspect now, run in its
own request rather than concurrently in one pass, because later stages need earlier stages'
answers. M4 (correspondence), M5 (submission mechanics), and M6 (cleanup) are unaffected in intent,
only in what feeds them (per-stage research output instead of `CorridorProfile`/pack data).

## The gaps this closes (verified in code, 2026-08-15)

- **G0** — no `(nationality, residence, destination, purpose)` corridor model at all; nothing
  can tell a Dhaka user whether Japan needs a visa, what route, or who files, before a case exists.
- **G0b** — `docs/jurisdictions/jp/tourist.new_application.yml` (`is_live: true`) is the
  **inverse** scenario (a JP resident's guarantor pack). A BD applicant scoping
  JP·tourist·new_application is wrongly asked for a 在留カード number. No selector mechanism exists
  to route by residence/nationality.
- **G1** — research is one shallow LLM pass over ≤6 destination-level pages;
  `OFFICIAL_DOMAINS["JP"]` never reaches `bd.emb-japan.go.jp`, where BD→JP truth (filing channel,
  documents, fee, processing time) actually lives.
- **G2** — `services/gov_scraper.py` is a second, citation-free, hardcoded-constant scraper
  (**currently a syntax error**, blocking `management/scrape_gov.py` and the scheduler fallback);
  `services/packet.py` hardcodes submission steps and **invented fee amounts** (NF-2 breach);
  `IntakeStep.tsx` has a fake OCR path writing literal fabricated values into real answers.
- **G3** — no correspondence layer; `PacketStep.tsx` fakes an "Official Embassy Cover Letter"
  client-side from a hardcoded template. No employer/sponsor letters, no appointment emails.
- **G4** — `IntakeQuestion` drops `section`/`citation` on serialization; 662 authored entries
  across the US packs never reach the browser.

Full research detail (schema map, service map, frontend map) lives in the session that produced
this doc — the design below is self-contained without it.

## Design (one paragraph per piece)

### Superseded design (kept for history — see Decisions §2)

Items 1–6 below described a `CorridorProfile` table + aspect-sharded-but-concurrent research +
a YAML pack selector + a hand-authored golden pack. That design assumed packs stay the primary
content source with research as a fallback. **Replaced** by the agentic per-stage engine in
"Current design" below. Mission domains (old §2) and question synthesis (old §4) are **not**
superseded — they're absorbed into the new engine as-is.

### Current design — the agentic per-stage engine

1. **One shared engine, four+one callers.** New `apps/ai/src/torii_ai/services/agentic_research.py`
   exposes `research_stage(request) -> StageResearchResult` for stage ∈
   `admissibility | intake | eligibility | documents | forms`. Each stage has its own
   context-aware query builder and its own narrow LLM extraction schema (reusing
   `ops_scraper.py`'s page-fetch/`_strip_html`/`_extract_json`/gov.uk-content-API helpers rather
   than duplicating them). `admissibility` is stage zero, run **before** a case exists (keyed by
   destination + purpose + action + nationality + residence, no `case_id`); the other four run
   **per case**, each seeded with everything learned so far (prior answers, the eligibility
   result, etc.) — sequential, not parallel, because stage N's queries depend on stage N-1's output.
2. **Two-round search per stage, not one.** Round 1: build queries from context → search
   (mission-domain-aware, see below) → scrape → LLM extract to the stage's schema, which also
   returns `insufficient: bool` and `followup_queries: string[]`. If `insufficient` and
   follow-ups exist, round 2 searches those specific queries and re-extracts, merging. This is the
   concrete shape of "search with LLM for additional info" for this iteration — a full multi-turn
   tool-calling agent is a natural later upgrade, not required to stop the static-content problem.
3. **Mission domains.** `official_domains_for(destination, nationality)` in `ops_scraper.py` unions
   destination-government domains with mission-in-origin domains (`bd.emb-japan.go.jp` for a BD
   national applying to JP) and never returns `None` (fixes a live crash for every destination
   outside the 17-entry map — already landed in M0).
4. **Question synthesis** (unchanged from the superseded design) — deterministic, in `apps/api`:
   every `forms[].field_mappings[].answer_key` with no matching question gets a stub. Runs after
   the `forms` stage's research, so the intake question set is always complete even where the
   LLM's own `intake` stage under-asked.
5. **Per-case, per-stage storage.** New `CaseStageResearch` table: `case_id`, `stage`, `status`,
   `payload`, `source_pages`, `error`, `researched_at`, unique per `(case_id, stage)`. Citation
   gate reuses `ops_ingest.validated_for_promote`'s discipline per stage (rules/documents need an
   `http` citation; forms need field mappings; questions need a `parse_questions`-compatible
   shape). `admissibility` results are cached by scope+nationality+residence (shared across
   applicants on the same corridor, like the old `CorridorProfile`); `intake`/`eligibility`/
   `documents`/`forms` results are per-case only, since they depend on this applicant's answers.
6. **Guidance reuses the existing `research` phase.** No new phase names: `compute_guidance` gains
   a `research_stage: str | None` field. Before entering `intake`, if `CaseStageResearch(case,
   "intake")` isn't ready, phase stays `research` with `research_stage="intake"`; same pattern
   before `eligibility` (stage `eligibility`), before `checklist` (stage `documents`), before
   `forms` (stage `forms`). `ResearchStep.tsx` already polls and renders a research timeline — it
   only needs the stage label to describe what's being researched, not a new UI.
7. **Correspondence** — extend `FormTemplate`/`CaseGeneratedForm` with `kind`/`audience`/
   `body_template`/`body_text`/`edited_body`; deterministic slot-fill + optional LLM prose draft,
   applicant-edited, never auto-sent.
8. **Submission mechanics from data** — `services/packet.py` reads the case's `admissibility`
   stage research instead of a hardcoded if/elif chain; no uncited number ever renders.
9. **Frontend** — `/scope` gains nationality + residence + an admissibility card before case
   creation; new `AdmissibilityStep`/`CorrespondenceStep`; `PacketStep` renders server data instead
   of client-generated text.
10. **Correctness fixes this depends on** — `IntakeQuestion` section/citation, fake-OCR removal,
    OCR path fix, token-key fix, `official_domains_for` None-safety, `QuestionType` "date",
    checklist `effective_from` enforcement, `operator: present` implementation, US pack
    duplication → alias instead of file clone, delete dead `EVISA_*` constants.
11. **Delete the dead static scraper** — `gov_scraper.py` + `scrape_gov.py` + the scheduler
    fallback, once mission-domain research covers what it was meant to backstop.

Full field-level shapes (migrations, endpoint signatures, pydantic models) are in the plan this
doc was generated from; expand each section here as it's implemented rather than duplicating
upfront.

## Milestones — log progress here as each completes

### M0 — Unblock and put authored depth on the wire ✅ DONE (2026-08-15)
- [x] Fix `gov_scraper.py` syntax error (restored the `ead` branch body; also restored the `l1`
      eligibility branch that the same in-progress edit had silently dropped)
- [x] `IntakeQuestion` += `section`, `citation`; confirmed they reach `GET /cases/{id}/intake`
- [x] Remove fake OCR literals from `IntakeStep.tsx` (deleted the whole "AI Smart Document
      Capture" simulation banner + `triggerAiDocumentOcr`, not just the literals — it had no
      real backing endpoint)
- [x] Fix OCR path `/assistant/ocr/…` → `/assistant/ai/ocr/…`
- [x] Fix token key (`"token"` → `"torii_token"`) in `ocr.ts`/`geo.ts`/`payments.ts`
- [x] `official_domains_for` crash fixed (log-line f-string no longer throws `TypeError` when
      `None`; the function itself still returns `None` for unmapped countries and `search()`
      already falls back to the settings allowlist in that case — the full "never returns None"
      redesign lands with mission domains in M1, this was the narrower live-crash fix)
- [x] Frontend `QuestionType` gains `"date"`
- [x] Verify: confirmed via API (`GET /cases/{id}/intake` for a properly-scoped `US·b1b2·new_application`
      case now returns 84 questions across 12 authored sections, 6 with citations) **and** in the
      browser (dev servers + login as `applicant1@example.com`) — section tabs, per-section
      progress, and "Official Source" citation links all render; the fake OCR banner is gone.
      Note: an existing case scoped via legacy codes (`tourist`/`new`) still resolves the
      8-question generic fallback, not the b1b2 pack — that's the pre-existing scope/pack
      resolution gap M2's pack selector addresses, not a regression from this fix.

Commit: `49e21b9 fix(api,web,ai): M0 correctness fixes for corridor-aware flow`.
API (`uv run pytest`, 72 passed) and `apps/web` (`pnpm typecheck`, clean) both gate-clean;
`pnpm lint` fails on a pre-existing ESLint/eslintrc circular-JSON error unrelated to this branch
(reproduced identically with these changes stashed out).

### M1 — Shared agentic engine + admissibility stage (was "Corridor") ✅ DONE (2026-08-15)
- [x] `apps/ai/.../services/agentic_research.py`: `StageResearchRequest`/`Result`, per-stage query
      builders, per-stage extraction schemas, two-round search-if-insufficient
- [x] Mission domains in `ops_scraper.py` (`official_domains_for(destination, nationality)`,
      unions destination + mission-in-origin domains; still returns `None` only when truly
      nothing matches, which `search()` already handles — see M0's narrower crash-fix note)
- [x] New AI endpoint `POST /ai/agentic/research-stage`
- [x] `CaseStageResearch` model + migration `0013_case_stage_research` (upgrade/downgrade
      round-trip verified, then applied to the dev DB)
- [x] `services/agentic.py` (api-side): `scope_key`, `stage_is_usable`, `stage_items`,
      `stage_is_valid` (per-stage NF-2 citation+schema gate, reusing `has_citation` — renamed
      from `ops_ingest._has_citation` — and `parse_questions` the same way
      `validated_for_promote` already does for packs)
- [x] Outbox topic `case.stage_research.queued` + worker handler `run_stage_research`
      (generalized from `run_case_research`; single request/response, no NDJSON progress stream
      yet — a stage completes in well under a minute, streaming is a later addition if needed)
- [x] `admissibility` stage runnable pre-case (no `case_id`), cached by `scope_key`
      (destination+purpose+action+nationality+residence)
- [x] `POST /v1/corridors/check` + `GET /v1/corridors/{id}`, backed by the admissibility stage
- [ ] `/scope` admissibility card + `AdmissibilityStep.tsx` — **not started**, frontend wiring
      deferred to keep this milestone backend-complete and independently verifiable first
- [x] Verify: **full real stack** — `POST /v1/corridors/check` (BD nationality/residence, JP
      destination, tourist/new_application) → outbox → `run_stage_research` → real AI service →
      real Tavily reaching `bd.emb-japan.go.jp` (unreachable before the mission-domain fix) →
      real NVIDIA/Groq extraction → NF-2 gate passed → `GET /v1/corridors/1` returns: visa
      required, route `consular_visa`, filing channel `embassy`/filer `applicant` (no
      third-party agency needed for this corridor), the exact Dhaka embassy address, a 4-step
      process, and — genuinely case-specific, not generic — **the visa fee is 0 JPY for
      Bangladeshi nationals**, every fact cited to a `bd.emb-japan.go.jp` or `mofa.go.jp` page.

Commits: `0dec017` (shared engine + AI endpoint + model/migration),
`7102688` (api-side service + worker handler). Corridors endpoint + its 5 tests staged for the
next commit alongside this log update. API suite: 95 passed. AI suite: 33 passed.

### M2 — Intake stage wired end to end (was "Pack selector + golden pack" — deferred)
- [ ] `compute_guidance` gains `research_stage`; `research` phase reused for stage `intake`
- [ ] `cases.py:_intake_questions_for_case` stops reading `IntakeDefinition`/packs; always resolves
      via `CaseStageResearch(case, "intake")`, enqueuing when absent/stale
- [ ] `ResearchStep.tsx` renders `research_stage` in its timeline label
- [ ] Verify: a BD/BD→JP tourist case and a US/US→US b1b2 case produce **visibly different**
      intake question sets, live, with citations — the concrete fix for "same questions for every
      country"
- [ ] Existing pack-driven intake tests (`test_us02_intake.py`, `test_content_packs.py` intake
      assertions) updated to reflect research-driven intake; deterministic-logic tests
      (`validate_answer`, `progress_for`, `is_visible`) are unaffected and stay as-is

### M3 — Eligibility, documents, forms stages wired end to end
- [ ] Same pattern as M2 for `eligibility` (feeds `evaluate_eligibility` unchanged), `documents`
      (feeds checklist visibility unchanged), `forms` (feeds `fill_form` unchanged) — each stage's
      research call includes prior answers/results as context
- [ ] `question_synthesis.py`: every `forms` field mapping with no matching question gets a stub;
      wired in after the `forms` stage's research
- [ ] `test_question_coverage.py`
- [ ] Verify: full BD→JP walk — eligibility findings cited to BD-specific sources (not generic JP
      pages), checklist items match what the mission actually requires, forms match the real form
      the mission names

### M4 — Correspondence
- [ ] `FormTemplate`/`CaseGeneratedForm` schema extension + migration `0015_correspondence`
- [ ] `services/correspondence.py` (slot-fill + draft) + `POST /ai/correspondence/draft`
- [ ] `PUT /v1/cases/{id}/correspondence/{code}`
- [ ] `correspondence` guidance phase + `CorrespondenceStep.tsx`
- [ ] Verify: cover letter, employer leave letter, appointment email — generated, editable, saved

### M5 — Submission mechanics
- [ ] Rewrite `services/packet.py` off `CorridorProfile` data
- [ ] `PacketStep.tsx` renders server `submission_steps`/`dossier_order`; delete client generators
- [ ] Verify: no uncited number anywhere in the packet

### M6 — Cleanup
- [ ] Delete `gov_scraper.py` + `scrape_gov.py` + scheduler fallback branch
- [ ] Delete dead `EVISA_*` constants (superseded by `CorridorProfile.admission`)

## Tests

`test_corridor.py`, `test_pack_selector.py`, `test_question_coverage.py`,
`test_correspondence.py`, extended `test_content_packs.py`, extended
`apps/ai` `test_ops_scraper_general.py` (mission domains, None-safety, per-aspect queries).

## Risks

- Third-party filing routes: must say plainly who files, from the first screen.
- Aspect sharding multiplies LLM calls/cost per corridor — `CorridorProfile` (30d) and
  `ScopeResearch` (7d) TTLs are the cost control; `settings.research_aspects` is the dial.
- Mission sites are inconsistent — degrade to destination-level truth + "confirm with the
  mission," never an invented answer.
- Pack selector changes the seed uniqueness key — read `management/seed.py:_seed_workflow`
  before migration `0014`.

## Verification

`pnpm dev` + `torii-seed` → `/scope` BD/BD/JP/tourist/new_application → admissibility card cited
→ overseas pack intake (sectioned, cited, no residence-card question) → eligibility → checklist →
forms → correspondence → packet with sourced submission steps. Regression: JP-resident case still
gets the guarantor pack; US B1/B2 still resolves 94 questions.

`apps/api`: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`,
`uv run pytest`. `apps/web`: `pnpm lint`, `pnpm typecheck`, `pnpm build`. CI baseline on `main` is
red for known pre-existing reasons — verify each diff in isolation.
