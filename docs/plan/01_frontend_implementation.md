# Frontend implementation playbook — Applicant v1

> **Audience:** a small / freestanding coding agent implementing the Next.js applicant UI.  
> **Scope:** frontend only (`apps/web`). Backend is already on branch work that includes
> content packs, nationality intake, mock payments, and packet-download entitlement.  
> **Parent plan:** [`00_applicant_v1.md`](./00_applicant_v1.md) · product truth: `docs/specs/`.  
> **Last written:** 2026-08-02.

---

## 0. How to use this doc

Implement **one phase at a time**. After each phase:

1. Run from `apps/web`: `pnpm lint` and `pnpm typecheck`.
2. Manually smoke the user path listed under that phase.
3. Stop. Do not start the next phase in the same change set unless asked.

**Never:**

- Automate government portals or auto-submit DS-160 / ISA e-file (decision: guided-fill only).
- Invent fees, visa rules, or live jurisdictions without an official citation (NF-2).
- Store PII in `localStorage` beyond the auth token pattern already used.
- Add new packages without a clear gap (prefer existing `lib/api/*`, lucide, Tailwind, UI primitives).
- Drive-by refactors outside the phase file list.

**Always:**

- Match existing patterns in sibling files before inventing new ones.
- Use `token` from `useAuth()` and pass it into `lib/api/cases.ts` helpers (prefer that pattern).
- Keep `"use client"` on the smallest leaf that needs state/effects.
- Mobile-first: check ~360px width for forms and steppers.
- Surface errors from `Error.message` (API `detail`) to the user; do not swallow them.

---

## 1. Product flow (user journey)

```text
Landing (/) ──login──► /scope ──POST /cases/scope──► /cases/[id]
                              │
                              ▼
              ┌──────────────────────────────────────────┐
              │ Case pipeline (driven by guidance.phase) │
              │  intake → eligibility → checklist        │
              │  → forms → review → pay → packet → done  │
              └──────────────────────────────────────────┘
```

| Step | What the user does | API (prefix `/backend/v1`) |
|---|---|---|
| Scope | Pick destination, visa type, new vs renewal | `POST /cases/scope` |
| Guidance | See next action title + CTA | `GET /cases/{id}/guidance` |
| Intake | Answer questions; nationality is ISO enum | `GET /intake`, `PUT /intake/answer` |
| Eligibility | Rules check + citations | `POST /eligibility/evaluate`, `GET /eligibility` |
| Checklist | Gather / upload docs; OCR prefill | `POST /checklist/refresh`, `PATCH …`, `POST /documents` |
| Forms | Generate filled field maps | `POST /forms/generate`, `GET /forms` |
| Review | Fix flags; acknowledge | `POST /review`, `POST /review/acknowledge` |
| Pay | Mock checkout unlocking packet | `POST /payments/`, `POST /payments/{id}/process` |
| Packet | Build + download (402 if unpaid) | `POST /cases/{id}/packet`, `GET …/packet` |
| Submit | Only if e-file enabled (usually not) | `POST /cases/{id}/submit` |

Live beachhead scopes (content packs, after seed):

| Jurisdiction | Category | Action | Notes |
|---|---|---|---|
| JP | `work` | `renewal` | Single-stage beachhead |
| JP | `student` | `new_application` | Two stages planned later (UI stages later) |
| JP | `tourist` | `new_application` | Guarantor pack for resident in JP |
| US | `h1b` | `renewal` | Tests/specs use code `h1b` not `work` |
| US | `h1b` | `new_application` | Same |

**Scope mapping tip:** `/scope` currently uses geo visa codes. When creating a case, map UI “H-1B / work US” → `visa_category_code: "h1b"` and “New application” → `action_code: "new_application"` (not only `new` / `work`) so specialized packs apply.

---

## 2. Current frontend inventory (truth)

### Already implemented

| Area | Path | State |
|---|---|---|
| Case pipeline monolith | `apps/web/src/app/(app)/cases/[id]/page.tsx` (~1200 lines) | **Works**; step UIs are already function components **inside the same file** |
| Case API client | `apps/web/src/lib/api/cases.ts` | Full workflow helpers |
| Scope wizard | `apps/web/src/app/(app)/scope/page.tsx` | Geo-driven multi-step |
| Dashboard / cases list | `dashboard/page.tsx`, `cases/page.tsx` | List + next action labels |
| Profile | `profile/page.tsx` | Profile + avatar |
| Payments client | `lib/api/payments.ts` | Create / process / fees (mock) |
| Wallet client | `lib/api/wallet.ts` | Upload list |
| OCR client | `lib/api/ocr.ts` | Hits `/assistant/ocr/*` |
| Auth | `login`, `register`, `auth-context` | JWT in client |
| Landing i18n | `components/landing/dictionary.ts` | EN/JA landing only |
| Admin shell | `app/admin/*` | Staff; out of applicant scope unless noted |

### Missing / incomplete (implement in phases below)

| Gap | Severity |
|---|---|
| Step components not extracted to files | Blocks maintainability / stages |
| Packet step ignores payment + 402 entitlement | Blocks paid product |
| Landing `JURISDICTION_ORDER` hardcodes DE as third market | Live-scope drift |
| Authenticated app i18n (`locale="en"` hardcoded) | NF-5 / US-16 |
| No dedicated payment UI on case pipeline | M1 |
| Consent surfaces incomplete for passport upload | M1 legal precondition |
| Stage rail (two-stage cases) | M2 — wait for backend CaseStage |
| DS-160 guided-fill screen | M3 |

Backend already gates packet download:

- `GET /v1/cases/{id}/packet` → **402** when `require_packet_entitlement` and no completed payment.
- Frontend `getPacket` throws on non-OK; UI must treat **payment required** as a first-class state, not a generic error.

---

## 3. Architecture rules for this app

```text
apps/web/src/
  app/(app)/                 # applicant authenticated shell
    cases/[id]/page.tsx     # thin orchestrator after Phase A
  components/applicant/
    steps/                   # NEW — one file per pipeline step
    StageRail.tsx            # M2 only
    nav.ts, sidebar.tsx
  lib/api/                   # typed fetch wrappers → /backend/v1
  components/ui/             # Button, Card, Badge only
```

- **Server vs client:** most applicant pages are client (auth + interactive). Keep server components only where there is no client state.
- **No TanStack Query / RHF yet:** the case page uses plain `useState` + `useEffect`. Stay consistent unless a phase explicitly introduces a library.
- **API proxy:** browser calls `/backend/v1/...` (Next rewrite). Do not hardcode `localhost:8000` in components.
- **AI OCR:** `/assistant/ocr/...` (separate rewrite). Optional degradation: if OCR fails, still allow metadata document registration.

### Shared types already exported from `lib/api/cases.ts`

Use these — do not redefine:

`Case`, `CaseGuidance`, `IntakeState`, `IntakeQuestion`, `EligibilityResult`,
`ChecklistItem`, `Document`, `GeneratedForm`, `ReviewResult`.

### Guidance is the source of phase truth

```ts
guidance.phase: "intake" | "eligibility" | "checklist" | "forms" | "review" | "packet" | "done" | "blocked"
```

- `page.tsx` sets `activeStep` from `phaseToStep(guidance.phase)`.
- User may click a previous step in the rail only if sensible; never allow jumping past guidance without completing prior work (disable future steps if not yet unlocked by case status).

---

## 4. Phase A — Split case page into step components (M0)

### Goal

Leave behavior identical. Make `page.tsx` a thin shell so future StageRail / i18n / pay work is safe.

### Target layout

```text
apps/web/src/components/applicant/steps/
  types.ts              # Step, STEPS, phaseToStep, citation helpers
  IntakeStep.tsx
  EligibilityStep.tsx
  ChecklistStep.tsx
  FormsStep.tsx
  ReviewStep.tsx
  PacketStep.tsx
  index.ts              # re-exports
apps/web/src/app/(app)/cases/[id]/page.tsx   # orchestrator only
```

### What moves where

There are already **named functions** in `page.tsx` (approx lines):

| Function | File | Responsibilities to keep |
|---|---|---|
| `IntakeStep` | `IntakeStep.tsx` | Questions, profile autofill, answer PUT |
| `EligibilityStep` | `EligibilityStep.tsx` | Evaluate, show findings + citation links |
| `ChecklistStep` | `ChecklistStep.tsx` | Upload, OCR, wallet match, registerDocument |
| `FormsStep` | `FormsStep.tsx` | generateForms, missing fields |
| `ReviewStep` | `ReviewStep.tsx` | review + acknowledge |
| `PacketStep` | `PacketStep.tsx` | buildPacket, getPacket, download JSON (for now) |

`page.tsx` should keep:

- `loadCase` / `refreshGuidance`
- step data loading `useEffect` keyed by `activeStep`
- step rail UI, error banners, header
- pass **props down** (token, caseId, data, callbacks). Do not introduce global step stores.

### Props pattern (copy this shape)

```tsx
// example
type IntakeStepProps = {
  token: string;
  caseId: number;
  intake: IntakeState;
  profile: User | null;
  submitting: boolean;
  onAnswered: (next: IntakeState) => void;
  onAdvance: () => void;
  onError: (message: string) => void;
};
```

### Acceptance criteria

- [ ] `cases/[id]/page.tsx` is roughly &lt; 250 lines.
- [ ] No behavior change: same copy, same API calls, same step order.
- [ ] `pnpm typecheck` passes.
- [ ] Manual: open an existing case, walk intake → … → packet without console errors.

### Out of scope for Phase A

Do not add payments or i18n in this PR. Do not redesign visuals.

---

## 5. Phase B — Live scope truth + scope mapping (M0)

### Goal

One source of truth for “what is live” and correct category/action codes.

### Tasks

1. **Landing drift** — `components/landing/data.ts`  
   - `JURISDICTION_ORDER`: only show markets that are intentionally marketed. Prefer JP + US as `live: true`.  
   - Do **not** present DE as live.  
   - Prefer loading live jurisdictions from `GET /jurisdictions?live_only=true` for marketing sections when the user is not logged in only if a public endpoint exists; otherwise keep static marketing copy but keep flags aligned with seed (`JP`, `US` live for full workflows).

2. **`/scope` code mapping** — `app/(app)/scope/page.tsx`  
   When calling `scopeCase`:

   | UI selection | Send to API |
   |---|---|
   | Destination JP / US | `jurisdiction_code: "JP" \| "US"` |
   | US work / H-1B | `visa_category_code: "h1b"` (not `work` if H-1B pack required) |
   | New application | `action_code: "new_application"` where content packs use that string |
   | Renewal | `action_code: "renewal"` |

   Inspect `lib/api/geo.ts` application type codes. If geo returns `new`, map:

   ```ts
   const actionCode =
     selectedAppType.code === "new" ? "new_application" : selectedAppType.code;
   ```

   Similarly map US work → `h1b` when destination is US and visa type is work.

3. After create, link to `/cases/{id}` immediately (if not already).

### Acceptance criteria

- [ ] Starting JP work renewal loads specialized intake (includes `nationality`, not only generic questions).
- [ ] Starting US h1b pathway uses code that returns H-1B questions (`job_title`, degree, sponsor).
- [ ] Landing does not claim DE is live.

---

## 6. Phase C — Payment gate on Packet step (M1 frontend)

### Goal

User can pay (mock) before download; unpaid download shows paywall, not a broken error.

### API

```ts
// lib/api/payments.ts (exists)
createPayment(caseId, destinationCode, visaType)
processPayment(paymentId, "card")
getCasePayment(caseId)  // may 404 if none
```

Cases client:

```ts
buildPacket(token, caseId)   // always allowed to assemble when review OK
getPacket(token, caseId)     // 402 if unpaid (backend)
```

### UI flow on `PacketStep`

```text
1. User reaches packet phase (guidance says so)
2. Show "Build packet" → POST packet (snapshot on server)
3. If getPacket returns payment-required:
      show Paywall card (service fee + government fee disclaimer)
      CTA "Pay to download" → createPayment → processPayment (mock)
4. After payment completed, getPacket succeeds
5. Download button writes packet JSON (or PDF later when API adds binary)
```

### Implementation notes

1. Detect 402: today `req()` throws `Error` with `detail` string. Either:

   - Parse message containing `entitlement` / status by improving `req` to attach `status` on a custom error class, **or**
   - Add `getPacketAllowPaymentRequired` that returns `{ ok: false, status: 402 }`.

   Prefer a small typed error:

   ```ts
   export class ApiError extends Error {
     constructor(message: string, public status: number) { super(message); }
   }
   ```

   Apply in `cases.ts` `req()` only (or shared fetch helper if you introduce one).

2. Pass **jurisdiction code** and **visa type** into PacketStep for fee create:
   - From `caseData.jurisdiction_code` / category code on the case detail response if present; else from guidance/scope labels.

3. **Do not** trust UI alone: after “download”, always call API; if 402, re-open paywall.

4. Copy: government fees vs Torii service fee — never invent official government amounts without citation. Prefer showing **service fee** from payment preview; label government fee as “paid to government at filing” if amounts are unpublished.

### Acceptance criteria

- [ ] Unpaid user: cannot download packet; sees pay CTA.
- [ ] After mock pay: download works.
- [ ] Payment errors surface clearly.

---

## 7. Phase D — Wire payment earlier + polish checklist OCR

### Goal

Payment optional earlier (post-review), checklist upload UX solid.

### D1 — After Review

- On successful `acknowledgeReview`, optional card: “Unlock packet download — pay now or at packet step.”
- Same mock payment helpers.

### D2 — Checklist

Confirm `ChecklistStep` still:

1. Maps checklist `code` → OCR `DocumentType` (`passport`, `residence_card`, …).
2. Calls `extractFromFile` → previews fields → user confirms → `registerDocument` + `confirmDocument` + `patchChecklistItem(..., "uploaded")`.
3. Offers wallet docs when available (`getWallet`).

Improvements (only if broken):

- Disabled state while OCR runs.
- Show confidence; allow edit of extracted fields before confirm.
- If OCR endpoint down, allow “Mark gathered” without file (status `gathered`) so pipeline progress is not blocked for demos — do **not** skip required docs in production UX without marking incomplete.

---

## 8. Phase E — i18n on authenticated app (M1)

### Goal

Respect `Case.locale` and app language for chrome strings. Landing already has EN/JA dictionary patterns.

### Approach (minimal, no new dependency required)

1. Create `apps/web/src/components/applicant/i18n/dictionary.ts` mirroring landing style:

   ```ts
   export type AppLocale = "en" | "ja";
   export const appDictionary = { en: { ... }, ja: { ... } } as const;
   ```

2. Create `useAppLocale()` reading:

   - User preference (profile / local setting), default `en`.
   - Case detail: `caseData.locale` for content language toggles on the case page.

3. Wire `AssistantChat` with `locale={caseData.locale ?? appLocale}` instead of `"en"`.

4. Call existing `patchLocale(token, caseId, locale)` when user toggles case language.

5. **Content localization:** checklist/form names may already be `string | {en, ja}` from API — when rendering, if string is blank and object form appears in raw API JSON, pick by locale. If API already returns localized strings via `services/i18n.localized`, just display the string.

### Acceptance criteria

- [ ] Toggle EN/JA on case chrome updates labels.
- [ ] Assistant uses case locale.
- [ ] No hard dependency on incomplete Japanese translations: fall back to English key.

### Out of scope

Do not translate all admin pages. Do not change marketing landing patterns except reuse patterns.

---

## 9. Phase F — Privacy / consent surfaces (M1 UI stubs)

Backend may still evolve; ship UI that can attach when APIs exist.

### Minimum UI

1. **Before first passport upload** (ChecklistStep): checkbox  

   > I consent to Torii processing this document to prepare my application (not marketing).

   Block register/upload until checked for that session (local state). Store on escalation-like pattern if API gains a consent endpoint later; for now keep client gate + note in `registerDocument` metadata if backend allows `extracted_fields` / extend only if API accepts.

2. Profile or settings link text: “Export / erase data — contact support” **or** disabled buttons with copy that routes to existing legal email if no API yet. Label clearly “coming soon” only if true.

### Do not claim GDPR compliance you have not built.

---

## 10. Phase G — Stage rail (M2) — **blocked on backend**

Only start when API returns stages on case/guidance:

```ts
// expected future shape (illustrative)
guidance.current_stage?: { code: "sponsor_petition" | "applicant_filing"; sequence: number }
guidance.stages?: Array<{ code: string; status: string; actor: string }>
```

Then:

1. Add `components/applicant/StageRail.tsx` above the existing phase rail.
2. Show blocked message when stage waiting on COE / I-20 (from `guidance.blocked_reason` / instruction).
3. Do not invent stage state client-side.

---

## 11. Phase H — DS-160 guided fill (M3) — US only

New route or step panel for US consular forms:

- Left: our validated answers list with **Copy** buttons.  
- Right: plain-language explanation + official field name (US-17).  
- Link out to `travel.state.gov` form — **no automation**.  
- Code location candidate: `components/applicant/guided-fill/Ds160Guide.tsx`.

---

## 12. Orchestrator pseudo-code (post Phase A)

```tsx
// apps/web/src/app/(app)/cases/[id]/page.tsx
"use client";
// load case + guidance
// switch (activeStep) {
//   case "intake": return <IntakeStep ... />;
//   case "eligibility": return <EligibilityStep ... />;
//   ...
//   case "packet": return <PacketStep ... onPaid={refresh} />;
// }
```

Do not put business rules (eligibility math, form field inference) in the UI. Only display API results.

---

## 13. File touch map by phase

| Phase | Primary files |
|---|---|
| A | `cases/[id]/page.tsx` → `components/applicant/steps/*` |
| B | `scope/page.tsx`, `landing/data.ts`, maybe `lib/api/geo.ts` |
| C | `steps/PacketStep.tsx`, `lib/api/cases.ts` (ApiError), `lib/api/payments.ts` |
| D | `steps/ReviewStep.tsx`, `steps/ChecklistStep.tsx` |
| E | `components/applicant/i18n/*`, `(app)/layout` or sidebar, `assistant-chat.tsx` |
| F | `ChecklistStep.tsx`, optional profile page |
| G | `StageRail.tsx`, case page header |
| H | new guided-fill components + US forms step branch |

---

## 14. Manual verification script (every phase)

Prereqs:

```bash
# monorepo root — API + seed + web
# API: apps/api → uv run uvicorn ... ; torii-seed
# Web: apps/web → pnpm dev
```

Login: `applicant1@example.com` / `applicant-pass-123`

1. `/scope` → JP → work → renewal → create case.  
2. Complete intake (include nationality).  
3. Run eligibility.  
4. Refresh checklist; attach a passport image if OCR available.  
5. Generate forms → review → acknowledge.  
6. Packet: pay (after Phase C) → download.  
7. Locale toggle (after Phase E).

Regression: US h1b new_application still creates a specialized intake.

---

## 15. Definition of done for “frontend beachhead”

- [ ] Case page is modular (Phase A).  
- [ ] Scope creates live pack scopes correctly (Phase B).  
- [ ] Packet download is paywalled and recoverable with mock payment (Phase C).  
- [ ] App chrome can be JA/EN; assistant follows locale (Phase E).  
- [ ] Citations still render as links wherever findings show `citation.url`.  
- [ ] `pnpm lint` + `pnpm typecheck` clean for web.  

---

## 16. Ready-made agent prompts

Copy **one** phase prompt per session.

### Prompt — Phase A

```text
You are implementing Phase A only from docs/plan/01_frontend_implementation.md.
Extract step components from apps/web/src/app/(app)/cases/[id]/page.tsx into
apps/web/src/components/applicant/steps/* with no behavior change. page.tsx must become
a thin guidance.phase switch. Follow existing UI (Card, Button, Badge, lucide).
Run pnpm typecheck in apps/web. Do not add payments, i18n, or new dependencies.
```

### Prompt — Phase B

```text
Implement Phase B only from docs/plan/01_frontend_implementation.md.
Fix landing live-jurisdiction drift and map /scope createCase codes to content-pack
codes (h1b, new_application). Do not refactor the case detail page.
```

### Prompt — Phase C

```text
Implement Phase C only from docs/plan/01_frontend_implementation.md.
Add ApiError with HTTP status if needed. Wire PacketStep to mock payments and handle
402 packet entitlement. Use lib/api/payments.ts. No Stripe.
```

### Prompt — Phase E

```text
Implement Phase E only from docs/plan/01_frontend_implementation.md.
Add applicant dictionary EN/JA, wire Case.locale via patchLocale, fix AssistantChat locale.
Fallback to English. No new npm i18n library unless necessary.
```

---

## 17. Quick API reference (cases + payments)

Base: `GET/POST/PUT/PATCH` → `fetch("/backend/v1" + path)` with  
`Authorization: Bearer <token>` and `content-type: application/json`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/cases/scope` | Create case `{ jurisdiction_code, visa_category_code, action_code, locale? }` |
| GET | `/cases/{id}` | Case detail |
| GET | `/cases/{id}/guidance` | Next phase |
| GET | `/cases/{id}/intake` | Questions + answers + progress |
| PUT | `/cases/{id}/intake/answer` | `{ key, value }` |
| POST | `/cases/{id}/eligibility/evaluate` | Run rules |
| GET | `/cases/{id}/eligibility` | Last snapshot |
| POST | `/cases/{id}/checklist/refresh` | Materialize checklist |
| GET | `/cases/{id}/checklist` | Items |
| PATCH | `/cases/{id}/checklist/{itemId}` | `{ status: "gathered" \| "uploaded" }` |
| POST | `/cases/{id}/documents` | Register metadata + OCR fields |
| POST | `/cases/{id}/documents/{id}/confirm` | Confirm OCR |
| POST | `/cases/{id}/forms/generate` | Fill templates |
| GET | `/cases/{id}/forms` | List |
| POST | `/cases/{id}/review` | Flags |
| POST | `/cases/{id}/review/acknowledge` | Clear gate for packet |
| POST | `/cases/{id}/packet` | Assemble snapshot |
| GET | `/cases/{id}/packet` | Download JSON; **402 if unpaid** |
| PATCH | `/cases/{id}/locale` | `{ locale, host_locale? }` |
| POST | `/payments/` | `{ case_id, destination_code, visa_type }` |
| POST | `/payments/{id}/process` | `{ payment_method: "card" }` |
| GET | `/payments/case/{caseId}` | Latest payment |

---

## 18. Related docs

| Doc | Role |
|---|---|
| [`00_applicant_v1.md`](./00_applicant_v1.md) | Product sequencing / milestones |
| `docs/specs/00_overview.md` | What Torii is |
| `docs/specs/02_requirements.md` | US-NN requirements |
| `docs/jurisdictions/README.md` | Content pack schema (backend seed) |
| `docs/_shared.md` | Engineering standards |

When product truth conflicts with this playbook, **specs win**. When sequence conflicts, **00_applicant_v1** wins for product order; for step-by-step UI execution order, **this file wins**.
