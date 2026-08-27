# Making the content dynamic — plan

Goal: the agents supply the content; code supplies the mechanism. Written 2026-08-27, on
top of the boundary `03_corridor_bd_jp.md` already set — **the agent discovers what a rule,
document, form or step *is*, cited to an official source; deterministic code decides
whether a given applicant satisfies it.** Nothing below waives that.

That doc flagged two of these gaps already: **G2** (`packet.py` hardcodes submission steps
and invented fee amounts — an NF-2 breach) and **G3** (`PacketStep.tsx` fakes a cover letter
client-side). Both are now fixed, but by moving the hardcoding rather than removing it, which
is what this plan finishes.

---

## The honest split

Not everything should become dynamic. Three tiers, and the middle one is where most of the
remaining work is.

| Tier | What | Who authors it | Why |
|---|---|---|---|
| **A** | Filing steps, fees, offices, citations, which form a scope needs | **Agent**, citation-gated | Changes without warning, and is discoverable from official pages |
| **B** | Question wording, sections, gating, tick-box option labels | **Ops, in YAML** | Needs human judgement and review; changes often but not unpredictably |
| **C** | PDF field geometry, the layout fit gate | **Code** | A physical fact about a specific PDF revision; see *Why geometry stays* below |

### Why geometry stays in code

I tested deriving field positions from the printed labels rather than authoring them. It
resolves about 60% of fields and **silently mis-anchors the rest** — pypdf misreports the
text matrix for some runs by 400pt, and the name captions sit *below* the line they label.
Partial automation with silent failures is the wrong trade on a form somebody signs. What
geometry does have is a self-verifying gate: a fetched PDF that no longer matches its
authored layout is left blank rather than written into stale coordinates, so a stale layout
degrades safely instead of producing a wrong form.

So geometry is authored, and the *cost of a ministry revision* is a re-verification, not an
outage. That is the trade to keep.

---

## Step 1 — Consume the research the agent already does — DONE

`agentic_research.py` returns five stages, and the API consumes **four**:

```
admissibility → admission, filing_channel, process, fees, faq   ← only used pre-case
intake        → questions      ✓ consumed
eligibility   → rules          ✓ consumed
documents     → documents      ✓ consumed
forms         → forms          ✓ consumed
```

The `admissibility` stage already researches `process.steps` (ordered, with citations),
`fees` (amount + currency + citation) and `filing_channel` (embassy / consulate / visa
application centre / online portal, plus the mission URL). `services/submission_kit.py`
then hardcodes exactly that information for Japan, and `research.py` never exposes it.

**Do:** add `research_process()`, `research_fees()`, `research_filing_channel()` to
`services/research.py` alongside the four that exist, and let `build_submission_kit()` prefer
them, falling back to the authored JP facts when no usable research exists. Keep the
citation gate: a step with no `http` citation is dropped, not shown.

**Verify:** a BD→JP tourist case should get its filing channel from
`bd.emb-japan.go.jp` — which is the corridor truth `G1` says the current scraper never
reaches — rather than the generic mission directory the kit hardcodes today.

**Done.** `research_process_steps`, `research_processing_days`, `research_fees`,
`research_filing_channel` and `research_admission` now sit alongside the four that existed,
each gating on an `http` citation. `kit_from_research()` builds the kit from them and the
cover-letter/dossier route prefers it, keeping the authored per-procedure facts as the
fallback for a corridor nobody has researched yet.

A researched BD→JP tourist case now says: file through an accredited agency (not over the
counter), at the Embassy of Japan in Bangladesh, 3,000 BDT, 5–10 working days — none of
which follows from the destination alone. Covered by 7 tests in `test_submission_kit.py`.

---

## Step 2 — Citations table → agent-discovered, per item

`services/citations.py` is 359 lines and 36 hardcoded URLs, resolving a citation by
sniffing substrings out of an answer key (`"tax" in key`, `"pension" in key`, …). It has
already been wrong once: it synthesised `https://www.gov.jp/visa` for anything it could not
match, which reads as an official source and is not.

**Do:** every rule, document and form the agent discovers already carries its own citation.
Use that citation instead of re-deriving one from the key. Keep `citations.py` only as the
fallback for pack-authored items that predate per-item citations, and shrink it as packs are
re-researched.

**Verify:** `test_every_citation_url_in_the_resolver_is_a_real_official_url` already exists;
add one asserting an item's own citation wins over the topic table.

**Size:** ~1 day, mostly deleting.

**Done.** 359 lines to 143. The item's own citation now always wins, and the override that
replaced an authored citation whenever its URL looked "generic" to a heuristic is gone —
that one was showing applicants a source the item had never been checked against. What
remains is a fallback keyed on the scope the case is in, not on words in an item's key,
and the resolver no longer accepts an item key at all so the behaviour cannot creep back
in through a caller. `intake.py` also stopped guessing the jurisdiction from the key; it
read "cas" out of any key containing those letters and cited gov.uk for it.

---

## Step 3 — Form catalogue → agent-discovered content IDs

`jp_official_forms.py` pins 19 ministry content IDs and their SHA-256s. The store already
self-heals when a pinned URL stops resolving, by re-reading the status page — that discovery
logic works and is tested.

**Do:** promote discovery from fallback to first-class. A nightly job walks each status page,
records the current PDF URL and digest per (status, procedure), and writes a
`_form_revisions.yml` next to the packs. When a digest changes, the job opens a review rather
than silently adopting it, because a revised sheet may have moved a field.

**Do not:** let the agent author the *geometry* that follows from a revision (tier C).

**Verify:** `test_cached_templates_still_match_the_revision_the_layout_was_verified_against`
already fails on a revision. This turns that from a test failure into a queued review.

**Size:** ~2 days.

---

## Step 4 — UI metadata → the API already serves it

`FormsStep.tsx:getFormMetadata()` is a 100-line if/else chain of 14 form titles and URLs.
`GET /v1/cases/{id}/official-forms` already returns every one of those fields from the
catalogue.

**Do:** delete the chain, render from the response.

**Size:** ~2 hours. Pure deletion.

**Done.** The packs already author `official_title` and a citation per form; the API now
resolves that title at read time and the browser renders the publisher and revision from
the citation. The catalogue lookup by form code went with it — `official-forms` is keyed by
ministry code and generated rows by pack code, so it never matched anything.

---

## Step 5 — Tick-box options → ops YAML (tier B)

The 15 unauthored tick-box groups have two halves: *where the boxes are* (tier C, authored
with the layout) and *what each box means* (tier B — "Doctor", "Master", "Bachelor",
"Law", "Economics"…). Put the option labels and their answer values in
`_form_questions.yml` beside the question they belong to, so ops can correct a label without
a release.

**Size:** folded into the layout work, no separate cost.

**Done.** All fifteen groups are authored and marked from the applicant's answer, with the
option labels in `_form_questions.yml` carrying the form's own printed wording. Three
mechanisms came out of it, all in the layout rather than in code:

- `ChoiceField(style="tick")` beside the existing circle, and generic option matching, so a
  thirty-box group needs no per-key branch in the filler.
- `Flag` for the groups marked 複数選択可, where each box has its own amount line beside it.
  The box follows the amount and a zero leaves it clear.
- `Gate(key, values)` beside the boolean `depends_on`, for the 特定活動 sheet's routing
  table — "if you selected (2), fill in questions 18, 19, 27 and the signature" — carried
  into intake as `show_when.one_of`.

---

## Step 6 — Close the loop: agent proposes, ops promotes

Today research either goes live automatically (`validated_for_promote`) or not at all. For
tier A content that is fine. For tier B, the missing piece is a review surface.

**Do:** have the agent write proposed pack changes as a YAML diff against
`docs/jurisdictions/**`, surfaced through the existing `POST /v1/admin/ops/*` endpoints, with
the citation for each changed line. Ops accept or reject. This is what makes "my agents do it
all" reviewable rather than unbounded — the agent's proposal is versioned content, so a bad
proposal is a rejected diff, not a live regression.

**Size:** ~3 days, and it is the piece that makes steps 1–3 safe to run unattended.

---

## Order and cost

| Step | Cost | Payoff |
|---|---|---|
| ~~1. Consume `process`/`fees`/`filing_channel`~~ | **done** | Largest hardcoded table now agent-driven, citation-gated |
| ~~4. Delete `getFormMetadata()`~~ | **done** | 100 lines of guessed titles gone |
| ~~2. Per-item citations~~ | **done** | 359 lines to 143, and an NF-2 hazard removed |
| ~~5. Tick-box labels~~ | **done** | All 15 groups authored, labels in ops YAML |
| 3. Form revision discovery | 2 days | Ministry revisions become a queued review, not a silent break |
| 6. Propose/promote loop | 3 days | Makes 1–3 safe unattended |

About **5 days** left. Tier C stays, deliberately.

### Geometry: no longer outstanding

The 13 layouts and 15 tick-box groups this doc listed as remaining manual work are
authored. Every applicant sheet of every Japanese scope now fills and renders with each
value inside its printed box — 21 scopes, no unauthored pages. What is still the
applicant's own hand is named on the sheet: the work-history tables (intake has no
list-valued answer), the free-text box beside each 「その他」, and the signature date, which
the form itself requires the applicant to write.

Geometry is read with pdfium per-character boxes rather than the PDF text matrix, which
drifts by up to 80pt inside a kerned run. That is what made the tick-box groups tractable;
the earlier label-derived approach silently mis-anchored and was rejected for it.

---

## What this does not fix

Being explicit, because "fully dynamic" cannot mean all of it:

- **Geometry** stays authored — 13 layouts and 15 tick-box groups of manual work remain,
  and a ministry redesign will always need a human to re-verify.
- **The agent cannot invent an applicant's facts.** Every fabrication removed in this branch
  came from code filling a gap the applicant had left; an agent filling that same gap is the
  same defect with a better vocabulary. Dynamic content means the *requirements* are
  discovered, never the *answers*.
- **A citation gate is not a correctness gate.** It proves a source was cited, not that the
  source says what the agent claims. Spot-checking discovered content against the cited page
  stays a human job.

---

## The invariants any of this must keep

1. Rule-governed output is deterministic, never model-inferred (**NF-1**).
2. Nothing user-facing ships without an official-source citation (**NF-2**).
3. An unanswered field prints nothing — no placeholder that reads as an answer.
4. A layout that does not fit its PDF writes nothing at all.
5. Every gap is named on the document, so nobody is told a form is finished when it is not.

Guarded by `test_no_fabricated_answers.py`, `test_jp_official_forms.py`,
`test_submission_kit.py`.
