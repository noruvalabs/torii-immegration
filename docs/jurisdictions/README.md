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

## Loader

```python
from torii_api.services.content_packs import load_all_packs, load_pack_by_scope

packs = load_all_packs()
jp_work = load_pack_by_scope("jp/work.renewal")
```

Override the search path with `TORII_JURISDICTIONS_DIR` when needed.
