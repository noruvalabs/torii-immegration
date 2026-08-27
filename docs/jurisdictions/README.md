# Jurisdiction content packs

Versioned YAML is the source of truth for applicant workflows. `torii-seed` loads
these files into `IntakeDefinition`, `EligibilityRuleSet`, `DocumentRequirementSet`,
and `FormTemplate`. Ops can still edit live rows via `POST /v1/admin/ops/*`.

## Layout

```
docs/jurisdictions/
  README.md
  jp/
    _jurisdiction.yml
    work.renewal.yml
    student.new_application.yml
    student.renewal.yml
    student.change_of_status.yml
    tourist.new_application.yml
  us/
    _jurisdiction.yml
    h1b.renewal.yml
    h1b.new_application.yml
    f1.new_application.yml
    b1b2.new_application.yml
  uk/
    _jurisdiction.yml
    tourist.new_application.yml
```

## Pack shape

Every `*.yml` pack (not `_jurisdiction.yml`) must include:

| Key | Required | Notes |
|---|---|---|
| `scope` | yes | `jurisdiction`, `visa_category`, `action`, `is_live` |
| `stages` | yes | One or more stage descriptors (single-stage or two-stage) |
| `intake.questions` | yes | Same schema as `services/intake.py` |
| `eligibility.rules` | yes | Operators: `equals`, `min`, `max`, `in`, `nationality_in`, `not_empty` |
| `documents.items` | yes | Checklist items with `show_when` support |
| `forms[]` | yes | Official form code, version, citation, field mappings |
| `fees[]` | no | **Only publish amounts with an official citation** (NF-2) |
| `sources[]` | yes | Official URLs + retrieval date |

## Citation rule (NF-2)

Every eligibility rule, document requirement, fee, and form must carry a
citation with an `http` URL. Packs that fail this gate are rejected by
`ops_ingest.validated_for_promote` and by `test_content_packs.py`.

## Filing mode

Countries are filed with differently, and the deliverable follows. Declare it once in
`_jurisdiction.yml`:

```yaml
filing_mode: official_form_pdf   # a form is published to fill in and hand over (Japan)
filing_mode: online_portal       # the application is typed into a government site (UK)
filing_mode: hybrid              # an online application plus a form to print (US)
apply_url: https://www.gov.uk/browse/visas-immigration
```

`official_form_pdf` produces the filled ministry PDF. `online_portal` produces an
**answer pack** instead — the applicant's answers in the order the online service asks
for them, with the apply URL and an explicit list of what is still unanswered. UKVI
publishes no downloadable form, so a document styled as a UK application form would
misrepresent the process; the pack says on its face that it is not one.

The pack's sections come from the `form_field` prefix in the pack's own mappings:

```yaml
field_mappings:
  - form_field: personal.full_name      # "personal" becomes the section
    answer_key: full_name
    required: true
  - form_field: passport.passport_number
    answer_key: passport_number
```

Adding an online jurisdiction therefore needs no code — a `_jurisdiction.yml` with
`filing_mode: online_portal` and `section.field` mappings is enough.

## Never invent an answer

An unanswered field is printed as `NOT_PROVIDED` (`—`), never filled with a
plausible-looking value. These documents accompany a sworn application: a blank line
asks the applicant a question, an invented `"Passed approved SELT test at CEFR B1"`
makes a false statement to a government on their behalf. The same rule covers aliases —
a fallback answer key must be *the same fact under another name*, never a related one
(a guarantor's telephone is not the applicant's, a hotel is not a residence, a savings
figure is not a declaration of sufficient funds).

`tests/test_no_fabricated_answers.py` enforces all of this and fails on any new
fallback literal that is not `—`.

## Official form templates (JP)

Packs describe *what* a scope requires. The actual sheet the applicant signs is resolved
separately, because Japan issues a different published PDF for every
(residence status, procedure) pair — the Student extension form is not the Engineer
extension form, even though both are 別記第三十号の二様式.

That catalogue lives in `apps/api/src/torii_api/services/jp_official_forms.py`:

| Scope | Form |
|---|---|
| `*.new_application` | Certificate of Eligibility (別記第六号の三様式) + the MOFA consular visa form |
| `*.change_of_status` | Application for Change of Status of Residence (別記第三十号様式) |
| `*.renewal` | Application for Extension of Period of Stay (別記第三十号の二様式) |
| `permanent_resident.*` | Application for Permanent Residence (別記第三十四号様式 その１) |
| `tourist.new_application` | Visa Application Form to Enter Japan (MOFA) |

Each entry pins the ministry's content URL and the SHA-256 of the revision its field
geometry was verified against. Pre-warm the cache with:

```bash
torii-fetch-forms          # download anything missing
torii-fetch-forms --force  # re-download everything and report revisions
```

Templates are cached under `TORII_OFFICIAL_FORM_DIR` (default `./var/official_forms`)
with a sidecar JSON recording source URL, digest, and retrieval time. If a pinned URL
stops resolving, the store re-reads the ministry's status page to discover the current
one. If a fetched form no longer matches its verified layout, the blank official form is
served **unfilled** rather than written into stale coordinates —
`test_cached_templates_still_match_the_revision_the_layout_was_verified_against` is the
signal to re-verify.

Intake questions are extended from these forms at request time, so every box on the
sheet is asked about; pack-authored questions still win on any key they define.

### Editing those questions

They live in `jp/_form_questions.yml`, not in Python — wording, section and gating are
ops content:

```yaml
questions:
  employer_name:
    prompt: "What is the name of your employer?"
    type: string
    section: "Work & employer"
    max_length: 160
    show_when: { key: is_employed, equals: true }
```

`show_when` keeps intake short. A ministry form has whole blocks that most applicants
never fill — the guarantor block, the inviter block, the employer block — and asking all
of them of everyone is what made intake exhausting (a spouse applicant saw 74 questions,
of which 7 were required). Gate them behind one cheap yes/no and they are asked only once
they apply. The gate is emitted automatically just before the first question it controls,
so a gate must never be left unasked — `test_every_gate_a_question_depends_on_is_itself_asked`
enforces that.

Filing from abroad is two stages, and intake asks only for the form filed **next**: the
certificate of eligibility now, the consular visa once the certificate has been issued and
the applicant actually knows their flight and port of entry.

## Loader

```python
from torii_api.services.content_packs import load_all_packs, load_pack_by_scope

packs = load_all_packs()
jp_work = load_pack_by_scope("jp/work.renewal")
```

Override the search path with `TORII_JURISDICTIONS_DIR` when needed.
