# Torii Platform — Product Overview

> **Durable doc.** This folder (`docs/specs/`) is the canonical source of product truth for the
> Torii platform. It changes only when product direction changes — never to mirror
> implementation. It contains no implementation status and no phasing: whether something is built
> is answered by the codebase and its tests, and *when* something gets built is a planning
> decision made *from* this spec, recorded elsewhere. If anything else contradicts this folder,
> this folder wins.
>
> **Read order:** this doc (why) → [01_domain.md](01_domain.md) (domain literacy) →
> [02_requirements.md](02_requirements.md) (the verifiable contract) →
> [03_architecture.md](03_architecture.md) (one proposed realization) →
> [citation-contract.md](citation-contract.md) (the trust/legal wire contract).
>
> **Working name.** "Torii" (⛩️ — the gate one passes through to enter) is a placeholder codename.
> The product name is an open decision owned by the founder (see [02_requirements.md](02_requirements.md) §7).

## What the Torii platform is

Torii is a **guided form-preparation platform for immigration** — a TurboTax for visas. It walks a
person through renewing a visa, changing status, or filing a new application: a conversational
intake, an eligibility read, a personalized document checklist, auto-filled government forms, a
final consistency check, and post-submission tracking with renewal reminders. Every instruction it
shows links to the official government source it came from.

It is deliberately **not a legal advisor**. It helps a person complete government forms based on
their own inputs — the same legally-established lane TurboTax and LegalZoom occupy — and routes to a
licensed professional the moment a case leaves that lane.

The platform is:

- an **applicant app** (web, mobile-first, multilingual) that takes a person from "which forms do I
  even need?" to a submission-ready packet — guided intake, eligibility flags, document checklist,
  form generation, review, and status tracking;
- an **AI assistant** over the same app (and later chat channels) that answers procedural questions
  from official sources, captures documents from photos, and escalates to a human whenever the case
  is beyond its scope or its confidence;
- an **employer platform** for HR teams sponsoring foreign employees — bulk case management,
  compliance tracking, and deadline oversight across a workforce;
- a **back office** for the operations team: the knowledge base of government sources, form
  templates and field mappings, jurisdiction rules, a government-change monitor, and the human
  review queue for escalated cases;
- a **lawyer referral seam** that hands complex cases to partner immigration counsel — protecting
  the applicant, protecting the platform legally, and creating a revenue channel.

Every case — self-serve applicant, employer-managed, or lawyer-referred — lives in **one canonical
case pipeline** with one status lifecycle, one document vault, one citation trail, and one history.

## Who it serves

| Priority | Persona | ID | In one line |
|---|---|---|---|
| P0 | Applicant | APP | A foreigner renewing/changing/filing a visa; multilingual, anxious, cost-sensitive, deadline-driven, mobile-first. |
| P0 | Operations / content ops | OPS | Keeps the knowledge base, form templates, and jurisdiction rules current and correct; works the human-review queue. |
| P1 | Employer / HR sponsor | EMP | Manages visa cases for a foreign workforce; needs compliance and deadline visibility across many people. |
| P1 | Immigration lawyer (partner) | LAW | Receives escalated complex cases; the professional the platform routes to, not competes with. |
| P1 | Overseer / admin | ADM | Owner-level; configures jurisdictions, pricing, roles; approves rule changes before they go live. |

**The assistant** appears in user stories by that name. It is a user-facing actor — a tireless,
always-cited caseworker — not an implementation detail.

## The job

The pain is universal and recurring: 280M+ migrants worldwide face confusing, high-stakes
paperwork every 1–3 years, and pay lawyers $500–$3,000 for what is often a procedurally
straightforward filing. Torii's job is to replace that intermediary for routine work at 10x lower
cost, without ever becoming the thing that gets a person's status wrong:

- **Turn "which forms?" into a guided path** — narrow scope by country, visa category, and action,
  then branch an intake that only asks what this case needs.
- **Price the risk of a mistake down to near zero** — deterministic rules for the parts that are
  rules; a final consistency check that catches the wrong date, the missing document, the stale
  form version before submission, not after rejection.
- **Make trust verifiable, not asserted** — every required form, document, and instruction links to
  the exact government page or regulation it comes from. If it can't be sourced, it isn't shown.
- **Know the edge of the lane** — detect discretionary, contested, or high-complexity cases and
  route them to a licensed professional, in plain language, without pretending to advise.
- **Be present across the renewal cycle** — track the submission, then remind the person before the
  next deadline, turning a one-time filing into a multi-year relationship.

## Naming

**Torii** is the working name of the business and the platform (placeholder — see
[02_requirements.md](02_requirements.md) §7). **The assistant** is the applicant/staff-facing AI
(product naming TBD). Code identifiers are functional, not product names.
