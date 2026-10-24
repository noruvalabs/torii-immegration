# torii-ai

Torii's **model-facing service** (FastAPI). Conversational assistant with citations,
intake narration, RAG, guardrails, OCR, and **autonomous visa research agent**. Rule-governed truth stays in
[`apps/api`](../api) — this service proposes; the API validates and persists
([`docs/specs/03_architecture.md`](../../docs/specs/03_architecture.md)).

Standalone [uv](https://docs.astral.sh/uv/) project. LLM: **Groq** (OpenAI-compatible).
Live search: **Tavily** (with strict citation anchoring to official government portals).

---

## 🤖 Strategic Decision: Proprietary AI Agent vs. Third-Party APIs

Torii chose to build and maintain its **own autonomous AI research agent** rather than licensing expensive third-party travel APIs (e.g. Sherpa, IATA Timatic).

### Key Advantages:
1. **Deeper Form & Document Intelligence**:
   - *Third-Party APIs* ($1,000–$5,000/mo) only return binary answers: *"Visa Required: Yes/No"*, validity length, and high-level health notices. They **cannot** supply official embassy PDF form field mappings, intake questionnaire schemas, or custom consular document templates (e.g., Japan Schedule of Stay, Bangladesh bank solvency formats).
   - *Torii AI Agent* autonomously searches official ministries of foreign affairs, extracts the exact required form fields into dynamic JSON schemas, and compiles precise document checklists.
2. **Extreme Cost Efficiency (~$10–$30 / month)**:
   - With PostgreSQL caching (`CaseStageResearch`) and a 30-day Time-To-Live (TTL), repeated corridor queries hit database cache in `< 10ms` with **$0 AI cost**.
   - Running Tavily search + Groq Llama/Qwen structured inference only incurs costs on fresh or expired corridor inquiries, keeping monthly operations under ~$30/mo.
3. **Automated Embassy Policy Drift Detection**:
   - A scheduled background worker monitors official government source URLs for changes (HTTP ETag / Last-Modified / content hash). When an embassy updates its rules or fee schedules, the agent re-scrapes the source, alerts ops staff, and invalidates stale caches.

*See full Architecture Decision Record: [`docs/decisions/0002-global-corridors-and-ai-agent-engine.md`](../../docs/decisions/0002-global-corridors-and-ai-agent-engine.md).*

---

## Run

```bash
cp ../../.env.example ../../.env   # repo-root file, shared with apps/api and apps/web — fill in TORII_AI_GROQ_API_KEY and TORII_AI_TAVILY_API_KEY
uv sync
uv run uvicorn torii_ai.main:app --reload --port 8001
#   GET /health
#   POST /ai/chat/session
#   POST /ai/chat/messages  (SSE)
#   Scalar docs at /docs
```

## Configuration (`TORII_AI_` env prefix)

Loaded from the single `.env` at the repo root (see `config.py`), not a local `apps/ai/.env` —
one file covers apps/api, apps/ai, and apps/web.

| Variable | Default | Purpose |
|---|---|---|
| `TORII_AI_GROQ_API_KEY` | (empty) | Groq API key |
| `TORII_AI_GROQ_MODEL` | `qwen/qwen3.6-27b` | Vision/OCR-capable model id |
| `TORII_AI_GROQ_EXTRACT_MODEL` | `openai/gpt-oss-120b` | Chat and structured-extraction model id |
| `TORII_AI_GROQ_BASE_URL` | Groq OpenAI URL | Compatible base URL |
| `TORII_AI_TAVILY_API_KEY` | (empty) | Tavily search key |
| `TORII_AI_API_BASE_URL` | `http://localhost:8000` | System-of-record API |
| `TORII_AI_SERVICE_TOKEN` | (empty) | Optional internal AI→API token |
| `TORII_AI_COOKIE_SECURE` | `false` | Set `true` behind HTTPS |

## Gates

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest
```

## Notes

- Citation contract: [`docs/specs/citation-contract.md`](../../docs/specs/citation-contract.md).
- Rotate any keys that were shared in chat before production use.
