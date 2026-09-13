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
#
# stdlib urllib, not httpx, and every 30s rather than 15s. Measured in this image on the
# deployment host: `import httpx` + one GET costs ~3.5s, urllib + the same GET ~1.2s (bare
# interpreter startup is ~0.5s of that). At the old 15s interval the api's own liveness probe
# was burning ~23% of a CPU in a continuous loop — on a host whose sustained baseline is a
# quarter of one core, and with the ai service paying the identical tax. This is ~6x cheaper
# and tests exactly the same thing.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=5).status==200 else 1)"

CMD ["sh", "-c", "exec uvicorn torii_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
