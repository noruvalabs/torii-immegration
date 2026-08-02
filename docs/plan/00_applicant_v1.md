# Applicant v1 — Japan + USA · student · work · tour

> **Planning doc — the sequencing layer.** `docs/specs/` is the canonical product truth and
> deliberately records no phasing or status. This document is the *when and in what order*, decided
> **from** that spec. If this doc and `docs/specs/` disagree on what the product **is**,
> `docs/specs/` wins. On sequence, this doc wins.
>
> **Read order for any agent or new engineer:** [`../specs/00_overview.md`](../specs/00_overview.md) →
> [`../specs/01_domain.md`](../specs/01_domain.md) →
> [`../specs/02_requirements.md`](../specs/02_requirements.md) → this doc.
>
> Last reviewed: 2026-07-30.

---

## 1. Context

**The goal.** Turn the applicant side of Torii into a sellable SaaS that removes paperwork hassle and
saves real money — the job Atlys, VisaHQ, iVisa, Sherpa, and AnyVisa do for tourist visas, done
properly for the filings where a professional currently charges ¥30,000–60,000. Two jurisdictions
(Japan, USA), three purposes (student, work, tour).

**This is not greenfield.** The applicant pipeline already exists and is tested end to end:

- `POST /v1/cases/scope` → intake → eligibility → checklist → documents → forms → review → packet →
  submit, in `apps/api/src/torii_api/api/case_workflow.py`, driven by one next-action engine:
  `services/guidance.py:compute_guidance`.
- Deterministic rule services: `services/{intake,eligibility,checklist,forms,review,packet}.py`.
- Ops-authorable content at runtime — `IntakeDefinition`, `EligibilityRuleSet`,
  `DocumentRequirementSet`, `FormTemplate` (JSON columns) via `POST /v1/admin/ops/*`.
- A government-source scraper with an auto-promote gate: `services/gov_scraper.py`,
  `services/ops_ingest.py`.
- Web: `/scope` wizard, `/cases/[id]` pipeline UI, `/assistant` (SSE), admin back office.
- Four live scopes seeded in `management/seed.py`: JP·work·renewal, JP·student·new_application,
  US·h1b·renewal, US·h1b·new_application.

So the work ahead is mostly **content plus two structural gaps**, not a rebuild.

### 1.1 Who the user is

A **foreign resident already living in Japan** — then global. This single decision reshapes both
jurisdictions:

- **Japan filings are domestic.** Filed by the applicant at a Regional Immigration Services Bureau or
  the ISA online system. **Self-filing is permitted**, so the 行政書士 licensing gate
  ([`../specs/02_requirements.md`](../specs/02_requirements.md) §7.2) is **not** a launch blocker for
  extension and change-of-status filings. This is the cheapest legal path to market and it is open
  today.
- **US filings are consular.** DS-160 plus an interview at the US Embassy Tokyo or a consulate in
  Japan. **Nationality**, not residence, decides the route.

### 1.2 The three jobs, in value order

| # | Job | Jurisdiction | Why it wins |
|---|---|---|---|
| **J1** | *Keep my status in Japan* — extension of period of stay, change of status | JP | Recurs every 1–3 years · 3.4M+ foreign residents · self-filing is legal · effectively no English-language competitor |
| **J2** | *Get to the USA from Japan* — F-1 study, H-1B work, B1/B2 or ESTA travel | US | High anxiety, high non-refundable fee at risk, well-documented forms |
| **J3** | *Bring my family to visit me in Japan* — short-stay / tourist | JP | The **resident** assembles the guarantor pack (招へい理由書 · 身元保証書 · 滞在予定表). Nobody serves this. This — not selling a ¥3,000 tourist visa to a stranger — is what "tour" means for our user. |

### 1.3 Timing — the wedge

The Immigration Services Agency has published fee increases taking effect **1 October 2026**.
Extension of period of stay and change of status move from a flat **¥6,000** (¥5,500 online) to a
banded schedule: roughly **¥10,000** (≤3 months) → **¥30,000** (1 year) → **¥60,000** (3 years) →
**¥70,000–75,000** (5+ years). The statutory ceiling was raised to ¥100,000 (¥300,000 for permanent
residence) by the amended Immigration Control Act promulgated 5 June 2026. Online filing keeps a
discount.

Three consequences the product should be built and marketed around:

1. **A rejected or refiled application now costs 5–12× what it did.** "Get it right the first time"
   stops being a soft benefit and becomes real money.
2. **The online-filing discount pushes every applicant toward the ISA online system** — exactly the
   channel our output packet should target.
3. **There is a narrow window to ship and own the message.**

> **Ops gate.** Final figures are set by Cabinet Order and were not final as of 2026-07-30. No fee
> number reaches a user without an official citation (NF-2). Until confirmed, fee fields stay
> unpublished rather than estimated.

### 1.4 Intended outcome

A resident in Japan pays roughly ¥5,000–15,000 instead of ¥30,000–60,000 to a 行政書士 (the
government fee is the same either way), completes a correct filing in about 30 minutes instead of
10–20 hours, and never files a stale form version.

---

## 2. Structural change: two-stage cases

Every non-trivial visa is **sponsor petition → applicant filing**. `Case` is single-stage today, so a
JP·student·new_application case produces a visa packet the applicant cannot yet file (no COE), and we
give no help with the part that actually takes 1–3 months.

| Scope | Stage 1 (actor) | Stage 2 (actor) |
|---|---|---|
| JP · work/student · renewal or change_of_status | — | applicant files at ISA — **single stage, ships first** |
| JP · work/student · new_application | employer/school files the COE inside Japan (sponsor) | applicant collects the visa at a Japanese embassy |
| JP · tourist · new_application (J3) | **the resident in Japan** assembles the guarantor/invitation pack (sponsor = our user) | visiting relative applies at an embassy, or eVISA |
| US · f1 | school issues the I-20; applicant pays the I-901 SEVIS fee | DS-160 + mandatory in-person interview |
| US · h1b | employer files the I-129 (+ cap registration) | DS-160 + interview |
| US · b1b2 / ESTA | — | single stage; nationality decides ESTA vs B1/B2 |

### 2.1 Design

Add an ordered `CaseStage` table; a `Case` owns 1..n stages.

- **`CaseStage`**: `case_id`, `sequence`, `code` (`sponsor_petition` | `applicant_filing`), `actor`
  (`applicant` | `sponsor`), `status` (reuse the existing lifecycle vocabulary),
  `blocked_by_stage_id`, `handoff_artifact` (`coe` | `i20` | `i129_approval`), and its own
  eligibility / checklist / forms / packet snapshots.
- **Move per-phase state off `Case` onto `CaseStage`**: `CaseChecklistItem`, `CaseGeneratedForm`,
  `eligibility_snapshot`, `packet_snapshot`. `Case` stays the container — scope, owner, `reference`,
  `locale`, `renewal_due_at`.
- **`compute_guidance` becomes stage-aware.** This is the highest-leverage edit in the plan. It
  already computes the single next action; extend it to compute that action *for the current stage*
  and to return a stage-blocked phase ("waiting on your school's COE — here's the pack to send them,
  here's what to expect"). Everything downstream — dashboard `next_title`, the case UI — inherits
  stage support for free, because it all reads `guidance`.
- Single-stage scopes get exactly one stage, so JP·renewal behaves exactly as it does today.

### 2.2 Migration

`0008_case_stages` — create `case_stages`; backfill one `applicant_filing` stage per existing case;
add `stage_id` to the three child tables and backfill from `case_id`; drop the old `case_id` columns.
Keep `case_id` as a denormalised convenience FK on children if query churn in `case_workflow.py`
becomes ugly.

### 2.3 Web

`apps/web/src/app/(app)/cases/[id]/page.tsx` is **917 lines** and already the bottleneck. Split it
*before* adding stages: extract `IntakeStep`, `EligibilityStep`, `ChecklistStep`, `FormsStep`,
`ReviewStep`, `PacketStep` into `components/applicant/steps/`, add a `StageRail` for stage 1 → 2, and
leave `page.tsx` as a thin `guidance.phase` switch.

---

## 3. Jurisdiction content packs

Authored rules currently live as **Python dict constants** inside
`services/{intake,eligibility,checklist,forms}.py` plus a 439-line `management/seed.py`. That does not
scale past a handful of scopes and it is not ops-editable without a deploy — even though the *tables*
already support runtime editing.

Move authored content into versioned YAML under `docs/jurisdictions/`, and make `seed.py` a loader
over it. The same JSON lands in the same tables; what changes is that ops (and a future admin UI) own
a reviewable file per scope, and `git log` becomes the change history that NF-9 wants.

```
docs/jurisdictions/
  README.md                      pack schema + authoring rules (every field needs a citation)
  jp/
    _jurisdiction.yml            code, name, host_locale, licensing note (self-filing lane), fees
    work.renewal.yml             ← already live in seed.py; port first, to prove the loader
    work.change_of_status.yml
    student.renewal.yml
    student.new_application.yml  two stages (COE → visa)
    work.new_application.yml     two stages
    tourist.new_application.yml  two stages; sponsor = our user (J3)
  us/
    _jurisdiction.yml
    b1b2.new_application.yml     + ESTA branch on nationality
    f1.new_application.yml       two stages (I-20 / SEVIS → DS-160)
    h1b.new_application.yml      ← port from seed.py
    h1b.renewal.yml              ← port from seed.py
```

Each pack carries `intake.questions`, `eligibility.rules`, `documents.items`, `forms[]` (code,
official version, `official_title`, citation, `field_mappings`), `fees[]`, `stages[]`, and
`sources[]`.

**Every rule, document, fee, and form field mapping carries an official URL and a retrieval date.**
That is NF-2 and US-11.4, and `ops_ingest.validated_for_promote` already enforces it — the gate
exists, so use it.

### 3.1 Content to author (the real work — content, not code)

- **JP forms** — 在留期間更新許可申請書 (Extension of Period of Stay) and 在留資格変更許可申請書
  (Change of Status). Both are **per-category form sets**, so field mapping is category-dependent.
  Plus 在留資格認定証明書交付申請書 (COE). Source: `moj.go.jp/isa`.
- **JP J3 guarantor pack** — 招へい理由書, 身元保証書, 滞在予定表, plus the 住民票 / 課税証明書 the
  resident obtains locally. Source: `mofa.go.jp`.
- **US forms** — DS-160 (the universal nonimmigrant form), and the sponsor-side artifacts we *receive*
  rather than generate (I-20, I-129 approval notice, I-901 receipt). Sources: `travel.state.gov`,
  `ice.gov/sevis`.
- **Eligibility rules to add** —
  - JP work: **JLPT N2** is now required for standard corporate work statuses (effective April 2026).
    Add as a `fail` / `at_risk` rule with an official citation.
  - US F/M/J: an **in-person interview is mandatory** (no dropbox) since 2 September 2025, and all
    F/M/J applicants undergo online-presence review. Surface both as checklist items and
    expectation-setting — never as advice (US-12).
- **Fees** — for the money math in §5. Verified 2026-07-30: JP extension ¥6,000 counter / ¥5,500
  online, rising 1 Oct 2026 to the banded schedule in §1.3; US F-1 = $350 SEVIS + $185 MRV = $535
  minimum. Everything else is an ops task against a named source. **Do not ship an unverified
  number.**

### 3.2 Nationality becomes a first-class intake field

It gates two branches:

- **Japan eVISA eligibility for J3** — open to roughly 19 nationalities: AU, BR, KH, CA, SA, ZA, TW,
  UK, US apply directly; HK, IN, ID, MO, MN, KR, SG, AE apply via the Japanese consulate; PH and VN
  are package-tour only. Everyone else files on paper through an accredited agency.
- **ESTA vs B1/B2 for US tour** — a Japanese national travelling for tourism needs ESTA, not a visa.
  A non-VWP national resident in Japan needs B1/B2 at the embassy in Tokyo.

`services/intake.py` already has `TOP_COUNTRY_OPTIONS` (20 countries) and a `show_when` mechanism —
reuse both. Add a `nationality_in` operator to `services/eligibility.py` alongside
`equals` / `min` / `max` / `in`.

---

## 4. Build sequence

Each milestone is independently shippable and leaves `main` releasable.

### M0 — Foundations (unblocks everything; no user-visible change)

1. Split `cases/[id]/page.tsx` into step components (§2.3).
2. Build the `docs/jurisdictions/` schema + loader. Port JP·work·renewal from `seed.py` first and
   prove the seeded DB is identical. Then port the other three live scopes and delete the dict
   constants.
3. Add `nationality` to intake and the `nationality_in` eligibility operator.
4. Fix the live-scope drift: `apps/web/src/components/landing/data.ts` `JURISDICTION_ORDER` shows DE,
   while `seed.py` seeds 20 jurisdictions with only US and JP live. One source of truth for "what is
   live."

### M1 — Japan, single-stage, sellable (the beachhead; target: before 1 Oct 2026)

1. Content packs: `jp/work.renewal`, `jp/work.change_of_status`, `jp/student.renewal`.
2. **Real PDF output.** `services/packet.py` is 19 lines and assembles a JSON snapshot. Applicants
   need a filled, printable official form. Fill the ISA PDFs (`pypdf` / `pdf-lib` field mapping) and
   produce one print-ready packet plus a cover checklist (US-10.1, US-10.2).
3. **File upload + OCR wiring.** `POST /v1/cases/{id}/documents` is metadata-only — there is no binary
   seam at all. Add object storage (encrypted at rest, NF-4) and wire `apps/ai`'s OCR so passport and
   residence-card capture pre-fill intake (US-06). *This is the single biggest hassle reduction in the
   product and the main reason applicants will pay.*
4. **Payments.** Nothing exists — zero Stripe references in the codebase, though the landing page
   already advertises three tiers. Stripe Checkout plus an `Entitlement` model; gate packet download
   on entitlement, not on a UI check (US-22.2). Pay-per-application first; subscription later.
5. **Consent and privacy** (US-21) — data-processing consent recorded separately from marketing
   consent, plus export and erase. A legal precondition for accepting a passport upload, not a later
   polish item.
6. **i18n on the authenticated app.** The landing page is bilingual
   (`components/landing/dictionary.ts`), but the `(app)/*` surface is hardcoded English and
   `AssistantChat` is called with `locale="en"`. US-16 and NF-5 are unmet exactly where they matter
   most. Adopt one i18n library, wire `Case.locale`, and use `services/i18n.py:localized()` for
   content.

### M2 — Two-stage + Japan family visit (J3)

1. `CaseStage` model, `0008_case_stages` migration, stage-aware `compute_guidance`, `StageRail` UI.
2. `jp/tourist.new_application` — the guarantor pack. Differentiated, and it markets itself to the
   users you already have.
3. `jp/{student,work}.new_application` as true two-stage COE flows: generate the pack the applicant
   sends their school or employer, then the embassy visa stage.

### M3 — USA from Japan

1. `us/b1b2.new_application`, with the ESTA-vs-B1/B2 nationality branch.
2. `us/f1.new_application` — I-20 → I-901 → DS-160 → interview, with fee math and interview prep.
3. Port `us/h1b.*` to packs; two-stage with the I-129 handoff.
4. **DS-160 is a stateful web form with no API. Do not automate it.** Ship a *guided-fill* screen: our
   validated answer set beside the live official form, per-field copy buttons, official term plus
   plain-language explanation (US-17), and the applicant submits in their own session. A browser
   extension that fills the applicant's own session is a possible later step. Headless automation is
   out — CAPTCHAs, session timeouts, terms-of-service, and constant breakage. See
   `docs/decisions/0004-no-portal-automation.md`.

### M4 — Retention

US-18 status tracking (JP: ISA online status; US: CEAC), and turn on
`worker/scheduler.py:send_renewal_reminders`, which currently only logs. Renewal reminders are how a
one-off ¥5,000 filing becomes a multi-year relationship — US-19.3 already specifies pre-filling the
next case from the last one.

### Deliberately deferred

Employer platform (US-23/24 — the `EMPLOYER` role exists but there is no org model; it is also the
natural M5, given it is J1's sponsor side), lawyer-referral marketplace, analytics (US-31), and
appointment booking.

---

## 5. The money math

Only numbers with an official citation may be shown (NF-2). Verified 2026-07-30:

| Scenario | Today | With Torii | Saved |
|---|---|---|---|
| JP work-visa extension, 1 year, via 行政書士 | ¥30,000–60,000 professional fee + ¥6,000 government | our fee + ¥6,000 government | most of the professional fee |
| Same, **after 1 Oct 2026** | ¥30,000–60,000 + ~¥30,000 government | our fee + ~¥30,000 government (online discount) | the professional fee **and** the cost of a redo, now ~¥30,000 |
| US F-1 from Japan | $350 SEVIS + $185 MRV, non-refundable on refusal | same fees, correct the first time | the $535 you don't pay twice |

The honest claim is not "we make it cheaper" — the government fee is fixed. It is: **we remove the
intermediary's fee, and we remove the cost of getting it wrong.** After 1 October 2026 the second
half of that sentence becomes about 5× more expensive, which is the campaign.

Suggested pricing (the mechanism is US-22; the numbers are configuration): **¥4,900** scope +
checklist · **¥9,900** guided filing with forms and packet · **¥19,900** with human review by an
in-house reviewer. Anchored against ¥30,000–60,000 — not against iVisa's $50. We are not in the
tourist-visa price war.

---

## 6. Companion docs to write

| File | Contents |
|---|---|
| `docs/plan/README.md` | What `docs/plan/` is, read order, precedence vs `docs/specs/` |
| `docs/plan/01_money.md` | Fee tables per scope with citations, pricing model, unit economics vs 行政書士 |
| `docs/jurisdictions/README.md` | Pack schema, the citation requirement, how to author and promote a scope |
| `docs/jurisdictions/{jp,us}/*.yml` | The content packs in §3 |
| `docs/decisions/0002-two-stage-cases.md` | ADR for `CaseStage` |
| `docs/decisions/0003-jurisdiction-content-packs.md` | ADR for YAML-over-code |
| `docs/decisions/0004-no-portal-automation.md` | ADR: guided-fill, not headless submission — records the reasoning so it is not relitigated |

**Making this visible to every AI agent.** `docs/_shared.md` is the one shared rules file that
`.claude/CLAUDE.md`, `.codex/codex.md`, `.opencode/AGENTS.md`, and `.cursor/` all inherit. Append a
short `## Product Context` section there — 6–10 lines, linking out rather than restating, because that
file loads into every agent's context on every task:

- Torii is a guided form-preparation platform, **not** legal advice — the UPL line in
  `docs/specs/01_domain.md` is binding.
- The user is a **foreign resident in Japan**. Japan filings are domestic and self-filed; US filings
  are consular via the embassy in Japan.
- Read order: `docs/specs/00_overview.md` → `01_domain.md` → `02_requirements.md` → then
  `docs/plan/00_applicant_v1.md` for what to build next.
- Two rules never to violate: **NF-1** — rule-governed output is deterministic, never model-inferred;
  **NF-2** — nothing user-facing ships without an official-source citation.
- Jurisdiction content lives in `docs/jurisdictions/*.yml`, not in Python constants.
- Do not automate government portals (`docs/decisions/0004`).

Also add `docs/plan/` and `docs/jurisdictions/` to the repository-layout block in the root
`README.md`.

---

## 7. Verification

### Per milestone, end to end

1. `pnpm dev` (SQLite, zero infra) → `torii-seed` → sign in as `applicant1@example.com` /
   `applicant-pass-123`.
2. Walk `/scope` → the new scope → intake → eligibility → checklist → upload a passport image →
   confirm the OCR-extracted values → generate forms → review → pay → download the packet.
   **Open the produced PDF and check it against the official form.** This is the one check that cannot
   be automated away, because a mis-mapped field is a rejection.
3. Two-stage: confirm a `jp/student.new_application` case parks at stage 1 with a sponsor pack and a
   clear "waiting on your school" state, and that stage 2 unlocks only once the COE is recorded.
4. Nationality gating: a Bangladeshi resident of Japan is **not** offered Japan eVISA for J3, and
   **is** routed to B1/B2 rather than ESTA for US tour; an eVISA-eligible nationality takes the other
   branch.
5. Switch locale to `ja` and confirm the authenticated app is genuinely translated — the regression
   most likely to be missed.

### Automated

Extend `apps/api/tests/`:

- `test_case_stages.py` — staging, blocking, and migration backfill.
- `test_content_packs.py` — every pack parses; every rule, document, and fee has an `http` citation
  (reuse `ops_ingest.validated_for_promote`).
- `test_pdf_fill.py` — golden-file field mapping per form version.
- `test_entitlements.py` — packet stays locked without payment.

Remember [`../specs/02_requirements.md`](../specs/02_requirements.md) §2: code existing is not the
requirement being met. Each `US-NN.M` needs an actual passing check.

### Baseline caveat

`.github/workflows/ci.yml` is newly added on the `applicant-type-things` branch and has not run
against `main`. Verify each diff in isolation rather than trusting the aggregate signal.

---

## 8. Open questions for the founder

Not blockers — flagged for the right moment.

1. **Human review capacity.** In-house reviewers are the chosen model. At ¥19,900 with review, one
   reviewer caps throughput. M1 should ship pay-per-application *without* the review tier, and add it
   once there is a reviewer to staff the queue — `/admin/review-queue` already exists.
2. **Final ISA fee figures** are set by Cabinet Order and were not final as of 2026-07-30. Ops must
   confirm before 1 October 2026; until then, fee fields stay unpublished rather than estimated.
3. **JP tourist is seeded `is_live=False`.** It goes live with M2, not before — J3 depends on the
   two-stage model.

### Decisions this plan closes in `docs/specs/02_requirements.md` §7

Append these as resolved (never renumber):

- **§7.2 Japan filing standing** → the self-filing lane, for in-Japan filings.
- **§7.3 Beachhead scope** → JP work and student, renewal and change of status.
- **§7.6 Pricing** → the tiers in §5 above.
- **§7.8 E-filing integrations** → guided-fill; no portal automation.

Items 4, 5, 7, and 9 remain open.
