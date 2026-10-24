# ADR 0002 — Global Corridors ($195 \times 195$) & Proprietary AI Agent Engine

**Date:** 2026-10-21 · **Status:** accepted

## Context

Torii aims to support international travelers from any passport country traveling to any destination country ($195 \times 195 = 38,025$ theoretical corridors). 

Two fundamental questions arose:
1. How do we handle 38,000+ corridor combinations without combinatorial explosion or building 38,000 individual pages/forms?
2. Should we purchase a subscription to an enterprise third-party Global Visa API (e.g. Sherpa, IATA Timatic) or utilize our own autonomous AI research agent (`apps/ai`)?

## Decisions

### 1. Proprietary AI Agent over Third-Party Global Travel APIs
We explicitly chose to build and run our **own autonomous AI research agent** (`apps/ai/src/torii_ai/services/agentic_research.py`) rather than paying for a third-party global visa API.

**Rationale:**
* **Form Field & Document Depth:** Third-party APIs (Sherpa, Timatic) only provide binary answers (*"Visa required: Yes/No"*, validity length, general health rules). They **do not** provide official embassy PDF form field mappings, typed application questionnaire schemas, or custom document templates (e.g. Japan Schedule of Stay, hospital invitations).
* **Cost Efficiency:** Enterprise travel APIs cost $1,000–$5,000/month in fixed licensing or $0.20+ per lookup. Running our own autonomous agent (Tavily search + Groq/LLM) with 30-day database caching costs only ~$10–$30/month at scale.
* **Proprietary Moat:** Torii maintains full ownership of its structured immigration database, forms master, and legal citations without vendor lock-in.

### 2. Destination Reciprocity Tiers (Collapsing 38,000 into ~300 Rules)
Embassies do not write 195 unique immigration laws. Each destination country categorizes all global passports into 3–4 standard reciprocity tiers:
* **Tier 1 (Visa-Exempt / Visa-Free):** 0 forms, 0 fees, entry based on valid passport and digital arrival card.
* **Tier 2 (eVisa / Portal Concierge):** Online portal registration, electronic fee payment, digital PDF e-visa.
* **Tier 3 (Consular Embassy Dossier):** Official typed application form, bank solvency verification, itinerary, in-person submission at VAC/embassy.

Policies are stored relationally as `applicable_passports: TEXT[]` arrays under each destination, making corridor resolution instant ($< 2\text{ms}$) via indexed SQL.

### 3. The 80/20 Universal Schema-Driven Form Engine
* **80% Core:** Universal baseline questions (Personal identity, passport data, travel dates, occupation, basic solvency) are shared across every visa route globally.
* **20% Modular Add-ons:** Route-specific and corridor-specific questions (e.g. DS-160 security checks for US, Schedule of Stay for Japan, hospital referrals for Indian medical visas, TB screening for high-risk origins) are dynamically appended to the intake recipe based on `show_when` conditional logic.

### 4. Background Execution & 30-Day TTL Caching
* **No Blocking LLM Calls in User Flow:** Live users are never forced to wait 15–20 seconds for an LLM call while navigating the site.
* **30-Day TTL:** Researched corridor rules are stored in `CaseStageResearch` with `ADMISSIBILITY_TTL_DAYS = 30`. Subsequent visitors get instant ($< 10\text{ms}$) cached responses from Postgres/SQLite.
* **Scheduled Watcher Bot:** Background schedulers ping official government citation URLs periodically to detect rule drift and automatically queue re-scraping when embassies update policies.

## Consequences

* The application can scale to cover all 195 countries worldwide with zero manual re-typing of 38,000 routes.
* Monthly AI infrastructure costs remain under $35/month regardless of traffic spikes, due to strict database caching.
* The frontend uses a single dynamic route (`/visa/[slug]?from=CODE`) and a single generic schema-driven form renderer that adapts to any visa worldwide.
