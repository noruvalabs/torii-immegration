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
   hand-authored."
3. When a corridor's official route requires a third party (accredited agency, VAC, sponsor),
   **prepare everything and hand off** — never block the case.
4. Letters/emails are **full LLM drafts, applicant-edited** — not fixed templates, not
   auto-sent.

Binding constraints, unchanged: **NF-1** rule-governed output is deterministic, never
model-inferred. **NF-2** nothing user-facing ships without an official-source citation.
No portal automation — guided-fill only.

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

1. **`CorridorProfile`** — new cached, citation-gated table keyed by
   `(destination, purpose, nationality, residence)`, resolved **before** a case exists via
   `POST /v1/corridors/check`. Payload: `admission` (visa required/route/max stay),
   `filing_channel` (who files, where, directory), `process` (steps, processing time,
   biometrics/interview), `fees`, `faq` — every leaf cited or dropped. `compute_guidance` gains a
   leading `admissibility` phase; a third-party filer is guidance, not a block.
2. **Mission domains** — `official_domains_for(destination, origin_country)` in
   `apps/ai/.../services/ops_scraper.py` unions destination domains with mission-in-origin domains
   (`bd.emb-japan.go.jp` for BD→JP) and **never returns `None`** (fixes a live crash for every
   country outside the current 17-entry map).
3. **Aspect-sharded research** — replace the single extraction pass with concurrent aspects
   (admissibility / channel / eligibility / documents / forms / questions / faq), each its own
   search → scrape → extract, merged deterministically by natural key.
4. **Question synthesis** — deterministic, in `apps/api`: every `forms[].field_mappings[].answer_key`
   with no matching question gets a stub (type inferred, citation copied from the form). This is
   what makes "all the common questions" a guarantee, not a hope.
5. **Pack selector** — `ScopeMeta.selector` (`residence_in`/`residence_not_in`/`nationality_in`/
   `nationality_not_in`) resolves which live definition wins; falls through to research when
   nothing matches. Fixes G0b.
6. **The golden BD→JP pack** — `docs/jurisdictions/jp/tourist.new_application.overseas.yml`,
   `selector: {residence_not_in: [JP]}`, authored to `us/b1b2` depth. The research-quality fixture.
7. **Correspondence** — extend `FormTemplate`/`CaseGeneratedForm` with `kind`/`audience`/
   `body_template`/`body_text`/`edited_body`; deterministic slot-fill + optional LLM prose draft,
   applicant-edited, never auto-sent.
8. **Submission mechanics from data** — `services/packet.py` reads the `CorridorProfile` payload
   instead of a hardcoded if/elif chain; no uncited number ever renders.
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

### M1 — Corridor
- [ ] `CorridorProfile` model + migration `0013_corridor_profiles`
- [ ] `services/corridor.py` + `api/corridors.py` (`POST /v1/corridors/check`, `GET /{id}`)
- [ ] `corridor.research.queued` outbox handler
- [ ] Mission domains in `ops_scraper.py`
- [ ] `admissibility` guidance phase + `corridor_third_party_filer` / `corridor_not_admissible`
- [ ] `/scope` admissibility card + `AdmissibilityStep.tsx`
- [ ] Verify: BD→JP corridor check returns route/filer/fee/processing-time, each cited

### M2 — Pack selector + the golden pack
- [ ] `PackSelector` model + `pack_matches` + `selector_specificity`
- [ ] Migration `0014_definition_selector`; fix `seed.py` upsert key
- [ ] Selector-aware resolution in `cases.py`/`case_workflow.py`, falling through to research
- [ ] `selector: {residence_in: [JP]}` on the existing guarantor pack
- [ ] `jp/tourist.new_application.overseas.yml` authored to B1/B2 depth
- [ ] Verify: BD/BD resolves overseas pack; JP-resident still resolves guarantor pack

### M3 — Deep research
- [ ] Aspect-sharded `research_aspects.py`, concurrent search/scrape/extract per aspect
- [ ] `question_synthesis.py` + wired into `run_case_research` and `seed.py`
- [ ] `test_question_coverage.py`
- [ ] `faq` slice end to end
- [ ] Research-quality gate: diff BD→JP research output against the golden pack, report recall

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
