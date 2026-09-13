# Readiness backlog — from working software to a sellable product

> **Purpose of this doc.** The execution backlog that follows the 2026-09-12 readiness review.
> Product truth: `docs/specs/`; sequencing precedence: `docs/plan/00_applicant_v1.md`. This doc
> is the working task list — it records *what to do, in what order, and how to know it is done*.
> It carries status; `docs/specs/` never does.

**How to use this.** Every task has a stable ID (`T-NN`), the review finding it closes
(`B-NN` / `JP-NN`), a size, and a verification line. Tick the checkbox only when the
verification passes — not when the code exists. Finding IDs come from the readiness review of
2026-09-12 and are stable; new tasks append, retired tasks are struck through, never reused.

**The one-line read.** Torii has solved the hard half — being correct and provable. The
unglamorous half is unbuilt: charging money, not re-typing a passport, telling anyone when
their visa expires, and noticing that Japan stopped requiring a trip to the counter.

---

## Phase map

| Phase | Theme | Window | Gate to leave it |
|---|---|---|---|
| **P0** | Fee correctness | **by 2026-10-01** | A JP case filed on 1 Oct quotes the right amount and the right payment method |
| **Phase 1** | Chargeable and defensible | 2–3 weeks | A completed case produces revenue and does not produce liability |
| **Phase 2** | Conversion and the online lane | 3–5 weeks | An applicant can finish on a phone and file from home |
| **Phase 3** | Price and retention | 4–6 weeks | A case is worth more than $19 and brings the applicant back |
| **Phase 4** | Scale | quarter+ | An agency can run forty cases a month on it |

Phases are ordered by dependency, not by appetite. Nothing in Phase 2 is worth building until
Phase 1 means a finished case produces revenue.

---

## P0 — Fee correctness, before 2026-10-01

ISA fee amounts and the payment method change for applications filed from 1 October 2026.
`00_applicant_v1.md` already records the constraint: *"Ops must confirm before 1 October 2026;
until then, fee fields stay unpublished rather than estimated."* This phase honours it.

**The estimate is smaller than it looks.** `resolve_fee()` already supports `channel`,
`effective_from`, `tiers` keyed by granted period, and a `published` flag — its docstring names
this exact October schedule as the case it must hide until confirmed. Draft tiered rows already
exist in three packs. This is authoring and wiring, not design.

### T-01 — Author the October fee bands in the remaining JP packs
**Finding:** JP-01 · **Size:** ~1 day · **Blocked by:** nothing

Draft rows exist in `work.renewal`, `student.renewal`, `student.change_of_status` — at
¥10,000 / ¥33,000 / ¥64,000 / ¥75,000 by granted period, `published: false`, cited to the
June 2026 public-comment page. Twelve of fifteen JP scope packs have nothing.

- [ ] Author a matching `*_tiered` fee row in the 12 remaining packs, `published: false`
- [ ] Each row carries its own citation with a retrieval date (NF-2); no figure without a source
- [ ] Author the `channel: online` counterpart where the online lane has a different amount
- [ ] **Verify:** `resolve_fee(as_of=date(2026,10,1))` returns a banded figure for every live JP
      scope, and returns the current figure for `as_of` before that date

### T-02 — Stop `_fee_note()` asserting a payment method
**Finding:** JP-01 · **Size:** ~2 hours · **Blocked by:** T-01

`submission_kit._fee_note()` ends every fee sentence with *"payable by revenue stamp
(収入印紙) on approval"*, unconditionally, and asks the resolver for `channel="counter"` first.
Both assertions stop being true on 1 October.

- [ ] Read the payment method from the fee row, not from a hardcoded suffix
- [ ] Take the channel from the case's chosen channel rather than defaulting to `counter`
- [ ] A fee row with no payment method stated prints the amount alone — never a guessed method
- [ ] **Verify:** extend `test_submission_kit.py` with a case dated after 2026-10-01 asserting
      the revenue-stamp sentence does not appear

### T-03 — Flip `published` when the Cabinet Order lands
**Finding:** JP-01 · **Size:** ~1 hour · **Blocked by:** T-01, an external event

- [ ] Watch for the final Cabinet Order; record its URL and date in the pack citations
- [ ] Flip `published: true` on the banded rows only after the figures are confirmed
- [ ] **Verify:** a case created on or after 1 October quotes the banded figure; one created
      before it quotes the current one. Both cite a real published source.

### T-04 — Fix the three stale ISA facts
**Finding:** JP-03 · **Size:** ~half a day · **Blocked by:** nothing

- [ ] `_ISA_ONLINE_URL` points at the pre-January landing page — update to the rebuilt system
- [ ] Re-run `torii-check-form-revisions`; every sha256 in `_ISA_CONTENT_IDS` predates the
      2026-01-05 rebuild and has not been checked since. Record drift as a queued review; **do
      not auto-adopt**
- [ ] **Verify:** `GET /v1/admin/ops/form-revisions` lists every JP form with its current
      digest and whether it matches the revision the layout was verified against

### T-05 — Write the filing-channel research down
**Finding:** JP-01…JP-05 · **Size:** ~1 day · **Blocked by:** nothing

Research that is not written down with its sources is not research Torii is allowed to ship
(NF-2). `docs/decisions/` currently holds exactly one ADR; the no-portal-automation decision
lives only as prose in `00_applicant_v1.md` §M3.

- [ ] `docs/plan/06_japan_filing_channels.md` — the ISA/MOFA channel research, every claim with
      its source URL and retrieval date
- [ ] `docs/decisions/0002-isa-filing-channels.md` — channels are per-scope; `efile_enabled`
      retired; the handoff boundary defined (Torii produces files, a person uploads them)
- [ ] `docs/decisions/0003-mynaportal-api-parked.md` — rejected for now, with reasons, so it is
      not re-researched next quarter: My Number Card requirement structurally excludes the
      overseas COE applicant; specs are NDA-gated; Digital Agency's own figure for the path is
      約半年から約1年
- [ ] **Verify:** a reader who has never seen this conversation can re-derive the channel matrix
      from the cited sources alone

---

## Phase 1 — Chargeable and defensible

Nothing here is interesting. All of it is load-bearing. A demo becomes a business in this phase
and not before.

### T-06 — Real payments
**Finding:** B-01 · **Size:** ~4 days · **Blocked by:** nothing · **Highest priority in the repo**

`services/payment.py` is titled "Mock payment service". `POST /v1/credits/top-up` increments
`user.credit_balance`, writes a ledger row reading *"Purchased … for $19.00"*, and returns
success **with no charge attempted**. Any authenticated user can loop it and mint unlimited
application passes.

- [ ] Stripe Checkout session per credit pack, in the pack's own currency
- [ ] Credits granted **only** on a verified `checkout.session.completed` webhook
- [ ] Webhook idempotency; the ledger row keys to the payment intent so a replay cannot double-credit
- [ ] Make the current `/top-up` path unreachable without a verified session
- [ ] Refund path that reverses the ledger rather than deleting it
- [ ] **Verify:** a test asserts `/top-up` with no payment session leaves `credit_balance`
      unchanged; a Stripe test-mode purchase end-to-end grants exactly one pack

### T-07 — Move the document vault off local disk
**Finding:** B-02 · **Size:** ~3 days · **Blocked by:** nothing

`wallet.py` writes to `Path("data/wallet_storage")` with `write_bytes`. No object storage, no
encryption at rest, no retention policy. This is the highest-sensitivity data the product
touches, stored in the weakest possible way — and it means the API cannot run more than one
instance, because a restart loses every applicant's passport.

- [ ] Object storage behind the existing `save_document_content` / `get_document_content` seam
      (the interface is already right; only the body changes)
- [ ] Server-side encryption with a named key
- [ ] Signed, short-lived read URLs — never a long-lived public object
- [ ] A retention policy, and a documented region so residency can be stated to a customer
- [ ] **Verify:** two API instances serve the same case's documents; killing one loses nothing

### T-08 — Subject access: export and erase
**Finding:** B-03 · **Size:** ~3 days · **Blocked by:** T-07

`C17` / `US-17` are P0 in the spec. The database carries one consent field —
`consent_to_share`, a boolean — and there is no export-my-data and no delete-my-account
endpoint anywhere.

- [ ] `GET /v1/me/export` — every case, answer, document and audit row for the signed-in user
- [ ] `DELETE /v1/me` — erase, with the audit trail of the erasure itself retained
- [ ] Separate, timestamped consent records for data processing and for marketing
- [ ] Surface both in the profile page, in plain language, in both languages
- [ ] **Verify:** an export round-trips a case; an erasure leaves no document in object storage

### T-09 — Token hardening
**Finding:** B-07 · **Size:** ~2 days · **Blocked by:** nothing

A 7-day, non-revocable access token in `localStorage`, read directly by six client modules.
One XSS on any applicant page is a week of access to a vault of passport scans, with no way to
revoke it.

- [ ] Short-lived access token, refresh token with rotation
- [ ] Server-side revocation on logout and on password change
- [ ] Move the token out of `localStorage` behind one accessor, so the storage decision is in
      one place rather than six
- [ ] **Verify:** a logged-out token is rejected by the API, not merely absent from the browser

### T-10 — Rate limits
**Finding:** B-08 · **Size:** ~1 day · **Blocked by:** nothing

No limiter, no quota middleware, no CORS configuration in either FastAPI app. Because credits
are free (T-06), one account can drive unbounded Tavily and Groq spend.

- [ ] Per-user and per-IP limits on every research, OCR, chat and export path
- [ ] An explicit CORS allowlist rather than relying on the proxy
- [ ] A per-user monthly research budget, enforced independently of credits
- [ ] **Verify:** a test asserts the limiter rejects the N+1th call within the window

### T-11 — Instrument the funnel
**Finding:** B-06 · **Size:** ~2 days · **Blocked by:** nothing

No error tracking and no product analytics in any of the three services. Every prioritisation
decision in Phase 2 is currently a guess and will stay one.

- [ ] Error tracking in api, ai and web, with the case reference on every event
- [ ] An event per journey phase entered and completed, so drop-off is visible per phase
- [ ] Per-case LLM and search cost recorded against the case, so unit economics are a number
- [ ] Alert on form-fill failures — today a form that fails to fill reaches the applicant before
      it reaches us
- [ ] **Verify:** a dashboard answers "which phase loses the most applicants" without a query

### T-12 — Non-blocking transactional email
**Finding:** B-11 · **Size:** ~half a day · **Blocked by:** nothing

`auth/email.py` uses synchronous `smtplib` with a 10-second timeout, called inline from five
async handlers. A slow mail provider degrades the whole API at exactly the moment — registration
— where latency costs the most.

- [ ] Enqueue mail through the existing outbox rather than sending inline
- [ ] **Verify:** a stalled SMTP host does not increase registration latency

### T-13 — Honest scope surface
**Finding:** B-09, JP-05 · **Size:** ~half a day · **Blocked by:** nothing

Two scopes are offered that have no deliverable behind them. This is the one class of defect
that destroys the trust the rest of the system exists to earn.

- [ ] UK to `is_live: false` until a real UK deliverable exists (three thin packs, no official
      form filling, and `var/official_forms/` holds ten PDFs, all `jp_*`)
- [ ] `tourist.renewal` and `tourist.change_of_status` resolve to no forms in `_scope_forms()`
      — correctly, since ISA residence forms do not apply to 短期滞在 — yet both packs are live
      at ~240 lines each. Either give them the counter procedure they represent, or make them
      unselectable
- [ ] **Verify:** a test asserts every live scope resolves to at least one form or an explicit
      "no form for this route" explanation

---

## Phase 2 — Conversion and the online lane

Phase 1 makes a finished case worth money. This phase is about more applicants finishing, and
about the channel Torii currently does not model at all.

### T-14 — Filing channels per scope
**Finding:** JP-02, JP-04 · **Size:** ~4 days · **Blocked by:** T-05

`FilingMode` is one string per country and `hybrid` is declared but never implemented. The law
varies per scope — and for `dependent`, by a *second person's* status. Six of Torii's eight
Japan scopes have an online route; the product offers none.

- [ ] `available_channels` and `default_channel` at the scope level, in the pack YAML, with
      `_jurisdiction.yml` as fallback
- [ ] `GET /v1/cases/{id}/filing` returns the set, with a **reason per unavailable channel**
- [ ] Retire `efile_enabled` — a boolean named "efile" gating a `POST /submit` reads as an
      unfinished integration rather than a deliberate boundary. `POST /filed` stays the real
      completion
- [ ] Channel picker at the packet step; the offline lane stays available for every scope, always
- [ ] **Verify:** a permanent-residence case offers no online lane and says why; a 短期滞在 case
      says 対象外; a `dependent` case whose supporter is out of scope says so. None of the three
      fails silently

### T-15 — Attachment compliance validator
**Finding:** §03 · **Size:** ~4 days · **Blocked by:** nothing · **Highest user value per unit of work**

ISA rejects non-conforming uploads **silently**. This is the constraint applicants fail without
being told why, and the PyMuPDF ingest stack to fix it is already in the repo. It improves the
offline lane too.

- [ ] Validate against ISA's rules: PDF only, ≤20 files, ≤25 MB total including the photo,
      ≥200 dpi, and **no password / print restriction / copy restriction**
- [ ] Photo handled separately: JPEG, 4:3, within 6 months
- [ ] Convert what can be converted; report what cannot, in the applicant's language
- [ ] Over the limit → surface 添付資料に係る申告書（参考様式９） so it does not read as a
      missing document
- [ ] **Verify:** a locked PDF, an oversized bundle and a 21st file each produce a named,
      actionable failure — never a pass

### T-16 — OCR into intake
**Finding:** B-04 · **Size:** ~5 days · **Blocked by:** nothing

The spec calls this the killer feature (`US-06.1`: extract fields *and pre-fill the
corresponding intake answers*). The extraction half is built. The pre-fill half does not exist
— `IntakeStep.tsx` contains no reference to OCR at all. Meanwhile a JP work renewal asks 52
questions by hand, including the passport number the OCR already read.

- [ ] Map extracted fields to intake answer keys through a declared mapping, per document type
- [ ] Every extracted value shown for review before it is used; nothing confirmed silently
      (`US-06.2`)
- [ ] Low confidence or unreadable → ask for re-capture or manual entry (`US-06.3`)
- [ ] **Verify:** a JP work renewal with a passport and residence card uploaded drops from 52
      hand-typed answers to under 20

### T-17 — Value before the wall
**Finding:** §05 · **Size:** ~4 days · **Blocked by:** nothing

Six gates stand between a visitor and anything they did not already know: register, verify
email, log in, five-step scope picker, research wait, 52-question intake. The eligibility read
and the checklist are the two most persuasive outputs and both are cheap to compute.

- [ ] Anonymous eligibility read and document checklist from a country/category/action triple
- [ ] Account required to **save**; payment required only for the **filled forms**
- [ ] **Verify:** a visitor reaches a personalised checklist without creating an account

### T-18 — Phone capture as the primary document path
**Finding:** §05 · **Size:** ~4 days · **Blocked by:** T-15

The spec says applicants are mobile-first and their documents are physical; upload is a file
picker. With the online lane this becomes load-bearing: the phone that photographs the residence
card is the same phone running the app that authenticates the filing.

- [ ] Camera capture with edge detection and a blur check before accept
- [ ] Capture feeds straight into an ISA-compliant PDF via T-15
- [ ] **Verify:** a full case completes on a phone, capture through packet, without a laptop

### T-19 — Stop re-researching the same corridor
**Finding:** §05 · **Size:** ~2 days · **Blocked by:** nothing

`ScopeResearch` caches with an expiry, but `CaseStageResearch` is keyed per case — so two
applicants on the same route each pay full latency and full API spend.

- [ ] Cache stage research by scope + corridor rather than by case
- [ ] Pre-warm the first two stages the moment the scope is picked
- [ ] **Verify:** the second case on an identical corridor reaches intake without a research wait

### T-20 — Intake completion model
**Finding:** §05 · **Size:** ~2 days · **Blocked by:** nothing

- [ ] "12 of 34 questions — about 9 minutes left", not a bare progress bar
- [ ] Group by document-gathering session, with named clean stopping points
- [ ] Let an applicant defer a question ("I'll get this from my residence card") so a blank does
      not read as a failure
- [ ] Show what changed when a re-evaluated branch clears earlier answers — `US-02.5` requires
      the re-evaluation, but silently losing answers reads as a bug
- [ ] **Verify:** a resumed case tells the applicant where they stopped and what remains

### T-21 — First frontend tests
**Finding:** B-10 · **Size:** ~3 days · **Blocked by:** T-14

31,100 lines of applicant-facing TypeScript with no tests. The backend's job is to refuse to
fabricate; the frontend's job is to not re-introduce fabrication in the rendering. Nothing
currently checks the second half.

- [ ] Playwright smoke test over the full journey — scope through packet — on both lanes
- [ ] An assertion that no step renders a value the API marked `NOT_PROVIDED`
- [ ] **Verify:** the suite runs in CI and fails on a deliberately broken step

---

## Phase 3 — Price and retention

Phase 2 gets more applicants to the end. This phase makes the end worth more than $19, and
makes them come back.

### T-22 — ISA answer pack
**Finding:** §03 · **Size:** ~3 days · **Blocked by:** T-14

Their own answers in the order ISA's screens ask for them, plus what is still blank.
`portal_pack.py` already does exactly this for the UK — it needs a Japanese section order, not
a rewrite.

- [ ] Japanese section order and wording, drawn from `_form_questions.yml` rather than new strings
- [ ] **Verify:** the pack's section order matches the live input screens, checked by hand once

### T-23 — Single-case CSV emitter
**Finding:** §03 · **Size:** ~5 days · **Blocked by:** T-22

ISA's own intermediate-save format: the user uploads it and the input screen fills itself. This
is the only artefact that removes the retyping, and retyping ~168 fields is where the
rejection-causing errors happen.

- [ ] Emit from the same `intake_answers` bag, with the same `NOT_PROVIDED` discipline — an
      unanswered field emits nothing, never a plausible placeholder
- [ ] **Pin the CSV template revision** in `_form_revisions.yml`. ISA reorders CSV columns
      between revisions, and a stale template silently loses the user's work — the same failure
      class the PDF layout fit-gate already guards against, and it needs the same gate
- [ ] **Verify — this one is non-negotiable:** upload a generated CSV to ISA's own input screen
      and confirm the fields populate. Until someone has done that by hand, the emitter is
      unproven and must not ship

### T-24 — Online filing steps
**Finding:** JP-03 · **Size:** ~2 days · **Blocked by:** T-14

`STEP_ONLINE = "online_portal"` is defined in `submission_kit.py` and referenced nowhere. The
slot exists and is empty.

- [ ] Author the ISA online step sequence: 利用者登録 → 利用申出 → input → attachments → submit
      → provisional receipt (~10 min by email) → formal receipt (next day) → outcome by the
      chosen 受領方法
- [ ] Surface the 特例期間 trap: a My Number Card expiring inside the grace period costs the
      applicant the ability to submit supplementary materials online, mid-case
- [ ] **Verify:** every step carries an official citation, or it is dropped rather than shown

### T-25 — Human review tier
**Finding:** §04 · **Size:** ~5 days · **Blocked by:** T-06

The highest-margin thing Torii can sell, and the thing customers ask for unprompted. The ops
review queue that serves it already exists.

- [ ] A paid tier at $79–129 routing the case into the existing review queue
- [ ] A stated, bounded promise on what the review covers — and what it does not (it is not
      legal advice; the UPL boundary in `01_domain.md` is binding here)
- [ ] Reviewer-facing diff of what the applicant entered against what the documents say
- [ ] **Verify:** a purchased review appears in the queue, is worked, and returns to the applicant

### T-26 — Reminders that actually send
**Finding:** B-05 · **Size:** ~3 days · **Blocked by:** T-12

`send_renewal_reminders` selects due cases, logs them, and returns a count. Its own docstring
says the dispatch is "the next step". Visas renew every 1–3 years; the reminder *is* the second
sale.

- [ ] Email dispatch through the outbox, in the applicant's language
- [ ] An `.ics` file for the renewal date and for the filing appointment — one file, large
      perceived value
- [ ] LINE for Japan-resident applicants, once email is proven
- [ ] **Verify:** a case with a renewal date inside the lead window produces a delivered message,
      not a log line

### T-27 — Outcome tracking
**Finding:** §04 · **Size:** ~1 day · **Blocked by:** nothing

The lifecycle ends at `packet` and `done`. Nothing records whether the application was
*approved*. So the one asset that justifies any price — "1,340 filings, 97% accepted" — never
accumulates, no matter how many cases run.

- [ ] An outcome field: approved / rejected / withdrawn / unknown
- [ ] A two-tap follow-up email at the expected decision date
- [ ] **Verify:** the acceptance rate is a query, and it compounds from case one

### T-28 — e-COE as a case outcome
**Finding:** §03 · **Size:** ~2 days · **Blocked by:** T-24

Choosing メール as the 受領方法 delivers the COE by email — forwardable abroad, presentable at
the mission and again at the border on a phone. It removes the international courier leg.

- [ ] Model the 受領方法 choice at filing, and the forwardable email as the artefact that feeds
      the consular leg
- [ ] Be explicit that e-COE and eVISA **do not chain** — eVISA is tourism-only
- [ ] **Verify:** a COE case shows the applicant the delivery method they chose and what arrives

### T-29 — Lawyer referral seam
**Finding:** §04 · **Size:** ~4 days · **Blocked by:** T-06

The escalation path is already specced and already detected (`US-13`). What is missing is the
handoff and the fee.

- [ ] Partner handoff with the case summary and citation trail attached
- [ ] Referral fee recorded against the case
- [ ] **Verify:** an escalated case reaches a partner with the routine work already done

### T-30 — The applicant's own language
**Finding:** B-12 · **Size:** ~4 days · **Blocked by:** nothing

`Lang = "en" | "ja"`. The corridor chosen to prove the product is Bangladesh → Japan. English
is the language of the applicant's *lawyer*, not the applicant.

- [ ] Bengali and Vietnamese on the applicant surfaces, starting with intake and checklist
- [ ] **Verify:** a full case completes in a language that is neither English nor Japanese

---

## Phase 4 — Scale

### T-31 — Bulk CSV for 取次者
**Finding:** §07 · **Size:** ~4 days · **Blocked by:** T-23, and an open spec question

ISA's bulk input takes up to 300 rows and is usable **only** by 取次者 — agencies and registered
filing agents, not applicants. The government has segmented the market. The single-case emitter
and the bulk emitter are the same field-mapping table with a different row count, which is why
applicant-first was the right order.

- [ ] Reuse T-23's mapping; do not fork it
- [ ] Blocked on 取次者 standing, still open in `docs/specs/02_requirements.md` §7
- [ ] **Verify:** a 300-row file round-trips through ISA's input screen

### T-32 — Agency / employer workspace
**Finding:** §07 · **Size:** ~3 weeks · **Blocked by:** T-31

The five-pack customers are agencies buying a consumer product sideways. `EMP` is already a
spec persona and there is already a stub admin page.

- [ ] Applicant roster, bulk case creation, deadline board across a workforce
- [ ] Seat pricing rather than per-case credits
- [ ] **Verify:** one operator runs forty cases without opening forty tabs

### T-33 — Second corridor, to Japanese depth
**Size:** ~1 quarter · **Blocked by:** Phase 3 complete

- [ ] Choose by where filing is a PDF or a published CSV rather than a closed portal — that is
      where the pipeline's advantage is real
- [ ] Do not widen before the first corridor converts; shallow coverage dilutes the claim

### T-34 — Sell the compliance story
**Size:** ~1 week · **Blocked by:** nothing

The citation trail, the audit history, the fit gate and the no-fabrication guarantee are
procurement assets. Nobody outside the repo knows they exist.

- [ ] A public page that states the guarantee and shows the mechanism
- [ ] **Verify:** a prospective agency customer can answer their own compliance questions
      without a call

---

## What this backlog does not cover

Being explicit, because a backlog that claims completeness is lying:

- **The regulatory research in §03 of the review is unverified by this repo.** The channel
  matrix, the upload constraints, the eVISA country list and the fee figures came from outside
  and carry a re-verification protocol (T-05). `mofa.go.jp` and `evisa.mofa.go.jp` return 403 to
  automated fetch — they must be opened in a browser and the retrieval date recorded by hand.
- **The CSV emitter is unproven until uploaded by hand** (T-23). No test in this repo can
  substitute for that one manual check.
- **Tier C geometry stays authored.** A ministry redesign will always need a human to
  re-verify; `05_remove_hardcoding.md` settled that trade deliberately and this backlog does not
  reopen it.
- **The Mynaportal API stays parked** — 6–12 months, NDA-gated specs, and a My Number Card
  requirement that structurally excludes the overseas COE applicant.
- **No estimate here is a commitment.** Sizes are for ordering, not for a date.

---

## The invariants every task above must keep

Unchanged from `05_remove_hardcoding.md`, and binding on everything in this document:

1. Rule-governed output is deterministic, never model-inferred (**NF-1**).
2. Nothing user-facing ships without an official-source citation (**NF-2**).
3. An unanswered field prints nothing — no placeholder that reads as an answer.
4. A layout that does not fit its PDF writes nothing at all. **T-23 extends this to the CSV
   template: a column order that does not match the pinned revision emits nothing.**
5. Every gap is named on the document, so nobody is told a form is finished when it is not.
6. **No portal automation.** Torii produces files; a person with their own credentials uploads
   them. No headless browser, no stored credentials, no request to a `.go.jp` host on an
   applicant's behalf. T-05 makes this a real ADR rather than prose in a plan doc.

Guarded by `test_no_fabricated_answers.py`, `test_jp_official_forms.py`,
`test_submission_kit.py` — and, from T-21, by the frontend suite.
