# Torii AI image — uv-managed, multi-stage. Mirrors apps/api/Dockerfile; the only differences
# are the entrypoint module and the port (8001).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (cached until the lockfile changes).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then the source and the project itself.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8001

# Liveness for compose/uptime probes. stdlib urllib rather than httpx, at half the old
# frequency — see the note in apps/api/Dockerfile for the measurements behind this.
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8001/health', timeout=5).status==200 else 1)"

CMD ["uvicorn", "torii_ai.main:app", "--host", "0.0.0.0", "--port", "8001"]
