# Torii Unified API + AI image — uv-managed, multi-stage.
# Built from the REPO ROOT:
#   docker build -f apps/api/Dockerfile .
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (cached until the lockfile changes).
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Then the API source and AI source.
COPY apps/api/ ./
COPY apps/ai/src/torii_ai ./src/torii_ai
RUN uv sync --frozen --no-dev

# Jurisdiction content:
COPY docs/jurisdictions ./docs/jurisdictions
ENV TORII_JURISDICTIONS_DIR=/app/docs/jurisdictions
ENV PYTHONPATH="/app/src:$PATH"
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Liveness for compose/uptime probes.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=5).status==200 else 1)"

CMD ["sh", "-c", "exec uvicorn torii_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
