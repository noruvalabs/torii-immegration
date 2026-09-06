#!/usr/bin/env bash
#
# Torii — one-time host preparation, run manually as root on a fresh deploy target BEFORE
# the first CI deploy:
#
#   scp infra/scripts/bootstrap-host.sh root@host:/tmp/ && ssh root@host 'bash /tmp/bootstrap-host.sh deploy'
#
# Creates the deploy user, the /opt/torii layout the deploy workflow writes into, and checks
# that Docker with the compose plugin is present. It deliberately does NOT install Docker or
# provision TLS — use the distro's documented Docker install, and terminate TLS at a host
# reverse proxy or load balancer in front of the published nginx port.
set -euo pipefail

DEPLOY_USER="${1:-deploy}"
APP_ROOT="${TORII_APP_ROOT:-/opt/torii}"

log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

log "Checking Docker"
command -v docker >/dev/null || { echo "Docker is not installed. See https://docs.docker.com/engine/install/" >&2; exit 1; }
docker compose version >/dev/null || { echo "The docker compose plugin is missing." >&2; exit 1; }
systemctl is-enabled docker >/dev/null 2>&1 || systemctl enable --now docker

log "Ensuring the $DEPLOY_USER user"
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$DEPLOY_USER"
fi
# The deploy workflow drives docker over SSH as this user.
usermod -aG docker "$DEPLOY_USER"
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
touch "/home/$DEPLOY_USER/.ssh/authorized_keys"
chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/authorized_keys"

log "Creating $APP_ROOT"
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" \
  "$APP_ROOT" "$APP_ROOT/compose" "$APP_ROOT/scripts" "$APP_ROOT/state" \
  "$APP_ROOT/nginx" "$APP_ROOT/nginx/conf.d"

cat <<EOF

Host prepared.

Remaining manual steps:
  1. Append the deploy public key to /home/$DEPLOY_USER/.ssh/authorized_keys
     (its private half becomes the DEPLOY_SSH_KEY repository secret).
  2. Base64 the production compose env file and store it as DEPLOY_ENV_FILE_B64:
       base64 -w0 infra/.env.example   # after filling in real values
  3. Point your TLS terminator at 127.0.0.1:\${NGINX_HTTP_PORT:-8080}.

See infra/README.md for the full secret list.
EOF
