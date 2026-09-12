#!/usr/bin/env bash
#
# Torii — production deploy, run ON THE HOST by .github/workflows/deploy.yml over SSH.
#
#   deploy.sh <image-owner> <tag>
#
# The host never builds. CI builds and pushes ghcr.io/<owner>/torii-{api,ai,web}:<tag>; this
# script pulls that exact tag, brings the stack up, smoke-tests the edge, and rolls back to
# the last tag that passed if anything fails.
#
# Required in the environment (the workflow exports them over the SSH session):
#   TORII_ENV_FILE_B64   base64 of the production compose .env
#   GHCR_USERNAME        GHCR login user
#   GHCR_TOKEN           GHCR token with read:packages
set -euo pipefail

APP_ROOT="${TORII_APP_ROOT:-/opt/torii}"
COMPOSE_DIR="$APP_ROOT/compose"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
ENV_FILE="$COMPOSE_DIR/.env"
STATE_DIR="$APP_ROOT/state"
CURRENT_TAG_FILE="$STATE_DIR/current-tag"
KNOWN_GOOD_TAG_FILE="$STATE_DIR/known-good-tag"

IMAGE_OWNER="${1:?usage: deploy.sh <image-owner> <tag>}"
TAG="${2:?usage: deploy.sh <image-owner> <tag>}"
export IMAGE_OWNER TAG

log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi
}

# `docker compose` with the deploy dir as the project directory, so the relative bind mount
# for the nginx conf (../nginx/conf.d/torii.conf) resolves exactly as it does in the repo.
compose() {
  docker compose --project-directory "$COMPOSE_DIR" -f "$COMPOSE_FILE" "$@"
}

cleanup_disk() {
  log "Ensuring host disk space"
  docker container prune -f >/dev/null 2>&1 || true
  docker builder prune -f >/dev/null 2>&1 || true

  local free_mb
  free_mb="$(df -m "$APP_ROOT" 2>/dev/null | awk 'NR==2 {print $4}' || true)"
  if [[ -n "$free_mb" && "$free_mb" =~ ^[0-9]+$ && "$free_mb" -lt 5000 ]]; then
    log "Disk space is low (${free_mb}MB free) — pruning images older than 24h"
    docker image prune -a -f --filter "until=24h" >/dev/null 2>&1 || true
  fi

  local free_mb_after
  free_mb_after="$(df -m "$APP_ROOT" 2>/dev/null | awk 'NR==2 {print $4}' || true)"
  if [[ -n "$free_mb_after" && "$free_mb_after" =~ ^[0-9]+$ && "$free_mb_after" -lt 2000 ]]; then
    log "Disk space critically low (${free_mb_after}MB free) — pruning all unused images"
    docker image prune -a -f >/dev/null 2>&1 || true
  fi
}

write_env_file() {
  log "Writing $ENV_FILE"
  umask 077
  printf '%s' "$TORII_ENV_FILE_B64" | base64 -d >"$ENV_FILE"
  chmod 600 "$ENV_FILE"
  # IMAGE_OWNER/TAG are exported above, which wins over anything stale in the file — but the
  # file is also what a human sees when they run `docker compose ps` by hand later.
  sed -i -e '/^IMAGE_OWNER=/d' -e '/^TAG=/d' -e '/^DEPLOY_SSH_/d' "$ENV_FILE"
  printf 'IMAGE_OWNER=%s\nTAG=%s\n' "$IMAGE_OWNER" "$TAG" >>"$ENV_FILE"
}

registry_login() {
  log "Logging in to ghcr.io"
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin >/dev/null
}

read_known_good_tag() {
  PREVIOUS_TAG=""
  if [[ -f "$KNOWN_GOOD_TAG_FILE" ]]; then
    PREVIOUS_TAG="$(tr -d '\r\n' <"$KNOWN_GOOD_TAG_FILE")"
  fi
}

# The published nginx port; the stack has no other host-facing surface.
edge_port() {
  local port
  port="$(grep -E '^NGINX_HTTP_PORT=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '\r' || true)"
  printf '%s' "${port:-8080}"
}

# `compose up --wait` already blocks on every container's own HEALTHCHECK. This is the extra
# check that the *edge* actually serves the new containers end to end.
smoke_test() {
  local port base
  port="$(edge_port)"
  base="http://127.0.0.1:${port}"
  log "Smoke-testing $base"
  local attempt
  for attempt in $(seq 1 30); do
    if curl -fsS --max-time 10 "$base/healthz" >/dev/null \
      && curl -fsS --max-time 10 "$base/backend/health" >/dev/null \
      && curl -fsS --max-time 10 "$base/assistant/health" >/dev/null \
      && curl -fsS --max-time 15 -o /dev/null "$base/"; then
      echo "Edge healthy after ${attempt} attempt(s)."
      return 0
    fi
    sleep 5
  done
  echo "Edge did not become healthy." >&2
  compose ps
  compose logs --tail 100
  return 1
}

rollback() {
  # Disarm the trap so a failing rollback can't recurse.
  trap - ERR
  if [[ -z "${PREVIOUS_TAG:-}" || "$PREVIOUS_TAG" == "$TAG" ]]; then
    echo "No distinct known-good tag to roll back to; leaving the stack as is." >&2
    exit 1
  fi
  log "Deploy failed — rolling back to $PREVIOUS_TAG"
  TAG="$PREVIOUS_TAG"
  export TAG
  sed -i -e '/^TAG=/d' "$ENV_FILE"
  printf 'TAG=%s\n' "$TAG" >>"$ENV_FILE"
  compose pull --quiet
  compose up -d --wait --wait-timeout 300 --no-build --remove-orphans
  printf '%s\n' "$TAG" >"$CURRENT_TAG_FILE"
  echo "Rolled back to $PREVIOUS_TAG." >&2
  exit 1
}

main() {
  require_env TORII_ENV_FILE_B64
  require_env GHCR_USERNAME
  require_env GHCR_TOKEN

  mkdir -p "$COMPOSE_DIR" "$STATE_DIR"
  chmod 700 "$APP_ROOT"

  cleanup_disk

  if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "Missing $COMPOSE_FILE — the workflow uploads it before running this script." >&2
    exit 1
  fi

  write_env_file
  registry_login
  read_known_good_tag

  trap rollback ERR

  log "Pulling ghcr.io/$IMAGE_OWNER/torii-{api,ai,web}:$TAG"
  compose pull --quiet

  log "Starting the stack"
  compose up -d --wait --wait-timeout 300 --no-build --remove-orphans

  smoke_test

  printf '%s\n' "$TAG" >"$CURRENT_TAG_FILE"
  printf '%s\n' "$TAG" >"$KNOWN_GOOD_TAG_FILE"
  trap - ERR

  # Keep recent release images for rollback; prune images older than 48h, stopped containers, and build cache.
  log "Pruning old images and build cache"
  docker container prune -f >/dev/null 2>&1 || true
  docker builder prune -f >/dev/null 2>&1 || true
  docker image prune -f >/dev/null 2>&1 || true
  docker image prune -a -f --filter "until=48h" >/dev/null 2>&1 || true

  log "Deployed $TAG"
  compose ps
}

main "$@"
