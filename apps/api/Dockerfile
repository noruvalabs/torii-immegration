# Torii API image — uv-managed, multi-stage. The worker reuses this image with a different
# command (see infra/compose/docker-compose.yml).
#
# Built from the REPO ROOT, not apps/api: the authored jurisdiction packs under
# docs/jurisdictions are a runtime dependency (seed rewrites from them on every boot, and the
# JP official-forms service reads _form_questions.yml per request), and Docker cannot COPY
# from outside the build context.
#   docker build -f apps/api/Dockerfile .
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (cached until the lockfile changes).
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then the source and the project itself.
COPY apps/api/ ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Jurisdiction content last: authoring a pack is then a one-layer rebuild, not a re-sync.
# The explicit path matters — resolve_packs_dir()'s monorepo-relative fallbacks do not apply
# to this layout.
COPY docs/jurisdictions ./docs/jurisdictions
ENV TORII_JURISDICTIONS_DIR=/app/docs/jurisdictions

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# Liveness for compose/uptime probes.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://localhost:8000/health').status_code==200 else 1)"

CMD ["uvicorn", "torii_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
