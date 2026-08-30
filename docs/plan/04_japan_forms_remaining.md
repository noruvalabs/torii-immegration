# Japan official forms — what is left

State of the JP official-form pipeline as of 2026-08-27. Numbers here are measured, not
estimated: run the snippet in [Measuring coverage](#measuring-coverage) to regenerate them.

Related: `docs/jurisdictions/README.md` (filing modes, template cache),
`apps/api/src/torii_api/services/jp_form_layouts.py` (geometry),
`apps/api/src/torii_api/services/jp_official_forms.py` (catalogue).

---

## Where it stands

**32 of 50 applicant sheets are filled** across the 19 published ISA forms. 7 of 20
layouts are authored; 13 remain.

| Status | Procedure | Applicant sheets | Filled | Remaining |
|---|---|---:|---:|---|
| work | extension | 2 | 2 | — |
| work | change of status | 2 | 2 | — |
| work | CoE | 2 | 2 | — |
| student | extension | 3 | 3 | — |
| student | change of status | 3 | 2 | p4 |
| student | CoE | 3 | 1 | p3, p4 |
| dependent | extension | 2 | 2 | — |
| dependent | change of status | 2 | 2 | — |
| dependent | CoE | 2 | 1 | p3 |
| spouse | extension | 3 | 3 | — |
| spouse | change of status | 3 | 3 | — |
| spouse | CoE | 3 | 2 | p4 |
| hsp | extension | 2 | 1 | p3 |
| hsp | change of status | 2 | 1 | p3 |
| hsp | CoE | 2 | 1 | p3 |
| designated activities | extension | 4 | 1 | p3, p4, p5 |
| designated activities | change of status | 4 | 1 | p3, p4, p5 |
| designated activities | CoE | 4 | 1 | p3, p4, p5 |
| permanent resident | — | 2 | 1 | p2 (様式その２) |

Page 1 of every form is complete, and the consular MOFA form is complete.

---

## 1. Layouts still to author (13)

Ordered by caseload. Each needs ruled-line geometry, a field map, question specs for any
new answer keys, and a visual check of the filled page.

| # | Layout | Sheets covered | Rows | Reference PDF |
|---|---|---:|---:|---|
| 1 | student part 3 — change of status | 1 | 14 | `930004076.pdf` p4 |
| 2 | student part 2 — CoE | 1 | 24 | `930004044.pdf` p3 |
| 3 | student part 3 — CoE | 1 | 13 | `930004044.pdf` p4 |
| 4 | dependent part 2 — CoE | 1 | 14 | `930004048.pdf` p3 |
| 5 | spouse part 3 — CoE | 1 | 19 | `930004054.pdf` p4 |
| 6 | hsp part 2 — extension + change | 2 | 18 | `930004096.pdf` p3 |
| 7 | hsp part 2 — CoE | 1 | 18 | `930004031.pdf` p3 |
| 8 | designated activities part 2 | 3 | 2 | `930004118.pdf` p3 |
| 9 | designated activities part 3 | 3 | 15 | `930004118.pdf` p4 |
| 10 | designated activities part 4 — extension | 1 | 19 | `930004118.pdf` p5 |
| 11 | designated activities part 4 — change | 1 | 16 | `930004088.pdf` p5 |
| 12 | designated activities part 4 — CoE | 1 | 16 | `930004058.pdf` p5 |
| 13 | permanent residence 様式その２ | 1 | 19 | `930002835.pdf` p2 |

**Why the CoE variants need separate layouts.** Same items, same order, different
coordinates — `fit_layout` rejects them against the extension nominal rows (residual
above tolerance), so they cannot share. Where they *can* share, they already do:
`_work_part2_lines()` serves both work sheets, with per-sheet date slots and an item
renumber offset.

**Authoring procedure**, per sheet:

```bash
# 1. geometry + captions + glyph positions
python scratchpad/pack.py jp_hsp_extension:2

# 2. look at the sheet
python scratchpad/render.py cache/jp_hsp_extension.pdf 2

# 3. author the FormLayout, bind it in _EXTRA_LAYOUTS, add QUESTION_SPECS
# 4. fill and render the result, check every value sits in its printed box
```

### Trap to avoid

Date slots and item numbers live in **each sheet's own coordinate space**. Sharing a
field map between two variants without parameterising them puts values in the wrong
place — this was caught on the work CoE sheet, where the shared map carried the
extension sheet's graduation-date coordinates. See `_work_part2_lines(graduation,
item_offset)`.

---

## 2. Tick-box matrices and repeating tables (15 items)

These sit on sheets that *are* authored, so the sheet fills but these specific items stay
blank. Each is named in the layout's `unsupported_items`, so the applicant is told, and
the note prints on the PDF.

| Item | Forms affected | Shape |
|---|---:|---|
| Final education — country and level | 3 | ~10 boxes |
| Major field of study | 3 | ~30 boxes |
| Method of support (beside each amount) | 5 | ~8 boxes |
| Personal relationship or status (spouse item 17) | 3 | ~30 boxes |
| Registered enrollment and school level | 2 | ~10 boxes |
| Supporter's relationship to applicant | 2 | ~7 boxes |
| Relationship of supporter / scholarship provider | 1 | ~15 boxes |
| Plan after graduation | 1 | 4 boxes |
| Work experience | 3 | repeating table, 3 rows |
| Japanese education history (high school only) | 2 | conditional block |

**Approach.** The mechanism already works — the CoE purpose-of-entry box is ticked this
way (`OfficialForm.purpose_checkbox`, `_draw_tick`). What is needed is a `checkboxes`
field on `FormLayout` mapping an answer value to a `Mark`, plus the glyph coordinates,
which `scratchpad/pack.py` already reports. Best done as one pass across all forms after
the text fields are in, since the boxes share a mechanism and several matrices repeat
across statuses.

The repeating **work-experience table** is different: it needs a list-valued answer
(`work_history: [{from, to, employer}]`), which intake has no question type for today.
That is a schema change, not just geometry — treat it separately.

---

## 3. Cover letter, dossier and filing kit — DONE

Filing instructions now come from `services/submission_kit.py`, derived per procedure
from the form catalogue, the pack's published fees and the case's own checklist. The
letter is addressed 法務大臣殿 for an ISA filing and to the consular section for a visa;
the dossier snapshot is titled from the form the case actually files.

Four false claims removed (all had been printed for every applicant): full immigration
compliance, substantiated employment income, `Tax / Pension Compliance: Certified
Compliant`, and a hardcoded four-row enclosure list. Also registered a CJK face — every
Japanese string in these documents had been rendering as tofu boxes.

Covered by `tests/test_submission_kit.py` (20 tests).

## 3b. Intake question volume — DONE

Conditional blocks are gated behind one yes/no, and intake asks only for the form filed
*next*. Across the measured scopes, 215 questions shown drops to 151; spouse goes from 74
to 38. The 130 questions moved to `docs/jurisdictions/jp/_form_questions.yml` so ops edit
wording, sections and gating without touching Python.

Trap worth knowing: a question gated on a key nobody is asked is unreachable forever and
its box prints blank. `test_every_gate_a_question_depends_on_is_itself_asked` guards it.

## 4. Smaller gaps

| Gap | Where | Note |
|---|---|---|
| US still produces a look-alike PDF | `pdf_generator.py`, `us/_jurisdiction.yml` | DS-160 is filed on the CEAC portal, so this should use the portal-pack path the UK now uses. `filing_mode` is **not** declared in the US pack — it defaults to `official_form_pdf`. |
| Form metadata hardcoded in the UI | `apps/web/.../FormsStep.tsx:35` | `getFormMetadata()` is a long if-chain of titles and URLs; the API now returns all of this from the catalogue |
| `tourist.renewal`, `tourist.change_of_status` resolve to no form | `jp_official_forms.py` | ISA publishes no dedicated sheet for a short stay; falls back to the generated summary. Correct today, worth confirming with a filing officer |
| Organisation sheets never filled | — | 所属機関等作成用 / 扶養者等作成用 are the employer's or school's to complete. Out of scope for the applicant flow, but a sponsor-facing flow would want them |
| `designated_activities` purpose box not ticked | `jp_official_forms.py` | The 特定活動 series covers several designations and the correct box depends on which; left for the applicant, and noted on the form |

---

## Measuring coverage

```python
import os, sys
sys.path.insert(0, "src")
os.environ["TORII_OFFICIAL_FORM_DIR"] = "var/official_forms"
from torii_api.management.fetch_forms import catalogue
from torii_api.services.official_form_filler import fill_flat_form

for form in catalogue():
    if form.layout is None:
        continue
    path = os.path.join(os.environ["TORII_OFFICIAL_FORM_DIR"], form.code + ".pdf")
    if not os.path.exists(path):
        continue
    result = fill_flat_form(form, open(path, "rb").read(), {})
    unfilled = [p for p in result.applicant_pages if p not in result.filled_pages]
    print(f"{form.code:42} {len(result.filled_pages)}/{len(result.applicant_pages)} {unfilled}")
```

Run `torii-fetch-forms` first to warm the cache.

## Invariants that must not regress

- A sheet whose layout does not fit is left **blank**, never written into stale
  coordinates. Page 1 failing to fit blocks the whole form.
- An unanswered field prints nothing — no placeholder that reads as an answer.
- An answer key may only be filled from a **different name for the same fact**, never a
  related one (`ANSWER_ALIASES`).
- Every unfilled applicant sheet and every unauthored item is named on the PDF, so the
  applicant is never told a form is finished when it is not.

Covered by `tests/test_jp_official_forms.py` and `tests/test_no_fabricated_answers.py`.
