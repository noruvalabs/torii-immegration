# `docs/plan/` — sequencing and implementation playbooks

Product **what** lives in `docs/specs/`. This folder is **when / in what order / how to execute**.

| Doc | Audience | Use for |
|---|---|---|
| [`00_applicant_v1.md`](./00_applicant_v1.md) | Product + eng | Milestones M0–M4, beachhead, deferred work |
| [`01_frontend_implementation.md`](./01_frontend_implementation.md) | Frontend agent (including small models) | Step-by-step Next.js applicant UI build |

## Read order

1. `docs/specs/00_overview.md` → `01_domain.md` → `02_requirements.md`  
2. `docs/plan/00_applicant_v1.md`  
3. For frontend agents: **this folder’s** `01_frontend_implementation.md`  
4. Content packs (backend): `docs/jurisdictions/README.md`

## Precedence

- Product definition: `docs/specs/` wins.  
- Milestone order: `00_applicant_v1.md` wins.  
- Concrete frontend file tasks and agent prompts: `01_frontend_implementation.md` wins.
