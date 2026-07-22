# Citation & sourcing contract

The wire contract for the platform's core trust and legal guarantee: **every customer-facing
instruction carries a verifiable citation to an official government source, or it is not shown**
(US-11, NF-2). This is the mechanism behind US-15 (grounded assistant) and part of what keeps the
product on the information side of the UPL line (US-12). It sits between `apps/ai` (which produces
instructions and their sources) and `apps/web` (which renders them) and is persisted by `apps/api`.

It also defines the assistant's chat transport, because a streamed answer must stream its citations
with it.

## The rule, precisely

An **instruction** is any customer-facing statement of what is required, what a form/field means,
what a document is for, or what an eligibility criterion says — anything a diligent applicant could
otherwise have read off a government page. Every instruction object has a non-empty `sources` array.

- The citation engine in `apps/ai` is the **only** producer of customer-facing instructions.
- **IF** a candidate instruction has no resolvable source, the engine **drops it** — it is never
  emitted, downgraded to "uncited", or shown with a placeholder (US-11.3).
- Rule-governed facts (visa→forms, eligibility, document requirements) originate in `apps/api`'s
  deterministic rules; each rule row carries the source ref(s) it was authored from, so its
  citations are structural, not model-generated (NF-1).
- Model-narrated content (plain-language explanations, assistant answers) must cite the retrieved
  passages it was grounded in; the engine verifies every emitted instruction resolves to a passage
  actually retrieved this turn, and drops any that don't.

## The `Citation` and `Instruction` shapes

```json
{
  "instruction_id": "uuid",
  "text": "Upload the Certificate of Eligibility your employer received from immigration.",
  "official_term": "在留資格認定証明書 / Certificate of Eligibility",
  "kind": "document_requirement",
  "sources": [
    {
      "source_id": "uuid",
      "authority": "Immigration Services Agency of Japan",
      "title": "Certificate of Eligibility — application documents",
      "ref": "Immigration Control Act Art. 7-1-2",
      "url": "https://www.isa.go.jp/…",
      "retrieved_at": "2026-07-01T00:00:00Z",
      "source_version": "2026-04"
    }
  ]
}
```

- `kind` ∈ `form_requirement | field_help | document_requirement | eligibility | process_step |
  timeline`. Fixes how the client renders it and which surface it belongs to.
- `official_term` is the exact legal/bureaucratic term, kept alongside the plain-language `text`
  (US-17.2). Nullable only where no official term applies.
- `sources` is **never empty**. `source_version` / `retrieved_at` are what make a later government
  change detectable (US-11.4, US-26): a citation pinned to `2026-04` is stale once the monitor sees
  `2026-07`, which flags the instruction's backing rule for review.
- `url` is the reachable official page; `ref` is the human-citable regulation/section. At least one
  of the two is present.

## Chat transport — SSE-over-POST

The assistant reply direction is one-way streaming (server → client) triggered by a discrete client
send; there is no client→server mid-turn signalling. That is Server-Sent Events, and it is the right
fit: a FastAPI `StreamingResponse` with `media_type: text/event-stream`, plain HTTP (only
`proxy_buffering off` on `/ai/` at the edge), an httpOnly session cookie for identity, and any
`fetch` client can read it — no WebSocket lifecycle, no SSE/WS client library. We use **POST** (not
the GET-only browser `EventSource`) so the request can carry a body and an `Authorization` header,
and read the streamed body incrementally.

### `POST /ai/chat/session`

Establish or refresh the anonymous session and load any prior transcript for the case (US-14.4).

- **Request:** `{ "case_id": "uuid-or-null" }`. Optional `Authorization: Bearer <token>` to link a
  signed-in applicant.
- **Cookie:** sets `ai_sid` (httpOnly, `SameSite=Lax`, `Secure`, `Path=/ai`) if absent. This id is
  the conversation identity and survives reloads.
- **Response `200`:**

  ```json
  {
    "conversation_id": "uuid-or-null",
    "locale": "en",
    "messages": [
      { "role": "user",      "content": "…", "created_at": "ISO-8601" },
      { "role": "assistant", "content": "…", "instructions": [ /* Instruction[] */ ],
        "created_at": "ISO-8601" }
    ]
  }
  ```

### `POST /ai/chat/messages`

Send one applicant message; the reply streams back as bubbles, each carrying its citations.

- **Request:** `{ "message": "…", "case_id": "uuid-or-null", "locale": "en" }`. Cookie `ai_sid`.
  Optional `Authorization`.
- **Success `200`, `Content-Type: text/event-stream`:** a sequence of `bubble` events, then one
  terminal `done` event. Each `bubble` carries its own `instructions` — the client renders no
  guidance text without its citations attached (the rule, on the wire):

  ```
  event: bubble
  data: {"index": 0, "text": "For a work-visa renewal you file the Application for Extension of Period of Stay.",
         "instructions": [ { "instruction_id": "…", "kind": "form_requirement",
                             "official_term": "在留期間更新許可申請",
                             "sources": [ { "authority": "ISA Japan", "ref": "…", "url": "…",
                                            "retrieved_at": "…", "source_version": "2026-04" } ] } ]}

  event: bubble
  data: {"index": 1, "text": "Want me to start that renewal from your saved details?", "instructions": []}

  event: done
  data: {"kind": "reply", "escalation_reason": null}
  ```

  - `kind` ∈ `reply | escalation | refusal`.
  - `escalation_reason` is non-null only when `kind == "escalation"` (`out_of_scope |
    low_confidence | requires_legal_advice | unsupported_request`) — the guardrail decided the case
    needs a professional (US-13) or the answer can't be grounded (US-15.2). The client renders the
    referral path.
  - `kind == "refusal"` means the guardrail blocked an advice-seeking request (US-15.3): a bubble
    explains the platform gives information, not advice, with no fabricated substance.
  - A conversational bubble with no guidance (`"instructions": []`) is allowed — the rule binds
    *instructions*, not small talk. Any bubble whose `text` states a requirement MUST carry a
    non-empty `instructions` array, or the citation engine drops the bubble before it reaches the
    wire.

- **Rate limited `429`, `application/json`:** `{ "kind": "rate_limited", "bubbles": ["…"] }`.

## Client responsibilities

1. On open: `POST /ai/chat/session` once → render `messages` (guidance text with its citation
   chips).
2. On send: append the user bubble locally, show a typing indicator, `POST /ai/chat/messages`;
   append each `bubble` with its citation chips; clear typing on the first bubble; stop on `done`.
   On `escalation`, render the referral CTA; on `refusal`, render the information-not-advice notice.
3. Never render an instruction's `text` without rendering its `sources` — the citation chip is not
   optional UI. A bubble that arrives claiming a requirement with empty `instructions` is a contract
   violation and should be surfaced as an error in dev, not shown as guidance.
4. Send `credentials: include` on every request so the cookie flows.

## Why this is its own doc

Because the guarantee is the product. "Cite every instruction" is the single strongest
trust-builder over a lawyer's black box, and the concrete thing that keeps generated guidance
inside the legal lane. Making it a wire contract — not a UI convention — means a bubble physically
cannot carry a requirement to the screen without its government source riding along, and a later
source change is detectable because every citation is version-pinned.
