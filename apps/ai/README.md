# torii-ai

Torii's **model-facing service** (FastAPI). Conversational assistant with citations,
intake narration, RAG (later), guardrails, and OCR (later). Rule-governed truth stays in
[`apps/api`](../api) — this service proposes; the API validates and persists
([`docs/specs/03_architecture.md`](../../docs/specs/03_architecture.md)).

Standalone [uv](https://docs.astral.sh/uv/) project. LLM: **Groq** (OpenAI-compatible).
Live search: **Tavily** (not a sole legal citation source).

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
| `TORII_AI_GROQ_MODEL` | `llama-3.3-70b-versatile` | Chat model id |
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
