#!/usr/bin/env bash
#
# Torii — one-shot host tuning for the small deployment VM.
#
#   sudo ./tune-host.sh            # kernel + docker daemon + journald
#   sudo ./tune-host.sh --trim-agents   # …and cut the Google Cloud Ops Agent back
#
# Idempotent: safe to re-run, and safe to run before or after a deploy. The Docker daemon
# restart at the end does not take the site down: `live-restore` (set below) keeps running
# containers up across it. Note the corollary — because the containers are not recreated,
# the `userland-proxy` change only takes effect for a port published after the next
# `docker compose up`.
#
# WHY THIS EXISTS
# The host is a GCE e2-micro: 964 MB of usable RAM and a 0.25 vCPU sustained baseline that
# bursts to 2. Measured on 2026-09-12, the resident set broke down roughly as:
#
#   Google Cloud Ops Agent (otelopscol + fluent-bit)   ~85 MB
#   google_osconfig + guest agents                     ~50 MB
#   dockerd + containerd + 7 shims                    ~185 MB
#   the seven application containers                  ~130 MB
#
# That is ~135 MB — about 14% of the entire machine — spent on GCP's telemetry agents before
# Torii gets a byte. With the rest committed, the kernel resorts to swap, and swapping onto a
# 10 GB persistent disk is what produced the load average of 9.4 at 49.7% iowait. The single
# most effective change available without resizing the VM is to stop paying for telemetry
# that nobody is reading.
set -euo pipefail

TRIM_AGENTS=0
SKIP_DOCKER=0
for arg in "$@"; do
  case "$arg" in
    --trim-agents) TRIM_AGENTS=1 ;;
    # Write daemon.json but leave the daemon alone. For when the stack is running and you
    # are not yet ready for it to be touched at all.
    --skip-docker) SKIP_DOCKER=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "Run me with sudo." >&2
  exit 1
fi

log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

# --- 1. Kernel VM + network ---------------------------------------------------
# swappiness 60 is a desktop default: it swaps anonymous pages out eagerly to grow the page
# cache. On a box whose disk is the bottleneck that trade is backwards — we would rather
# drop cached file pages (cheap to re-read) than page a live Python heap to disk.
log "Writing /etc/sysctl.d/99-torii.conf"
cat >/etc/sysctl.d/99-torii.conf <<'EOF'
# Torii small-host tuning. See infra/scripts/tune-host.sh for the reasoning.

# MUST COME FIRST, and must never be removed.
#
# Docker sets ip_forward=1 when the daemon starts, and it needs it: without
# forwarding, containers can still reach each other over the bridge but have no route
# off the host at all. GCE ships /etc/sysctl.d/60-gce-network-security.conf, which sets
# it back to 0. So any `sysctl --system` -- including the one this script runs to apply
# the settings below -- silently severs every container's outbound network.
#
# The failure is near-invisible: container-to-container traffic is unaffected, so
# healthchecks pass, nginx routes fine, and the site looks up. What breaks is only the
# things that leave the host: Google OAuth token verification, the LLM and search
# providers, and the government-source scraper. This file is 99-, so it sorts after
# 60-gce-network-security.conf and wins.
net.ipv4.ip_forward = 1

# Swap only under real pressure, not to grow the page cache.
vm.swappiness = 10
# Reclaim dentry/inode caches more readily than the default 100 would.
vm.vfs_cache_pressure = 50

# Start writing dirty pages back early and cap how many can accumulate. The defaults let a
# large fraction of RAM go dirty, then flush it all at once — on a slow disk that stall is
# indistinguishable from the site being down.
vm.dirty_background_ratio = 5
vm.dirty_ratio = 15

# Accept bursts of new connections rather than dropping them during a SYN spike. nginx's
# listen backlog cannot exceed this.
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
# Recycle closing sockets faster; with keepalive upstreams there are fewer of these, but
# 60s in FIN_WAIT is still needlessly long for a LAN hop.
net.ipv4.tcp_fin_timeout = 20
# Detect dead peers in ~5 min rather than the default ~2 h of held socket state.
net.ipv4.tcp_keepalive_time = 300
# Let the kernel reuse TIME_WAIT sockets for new outbound connections.
net.ipv4.tcp_tw_reuse = 1
EOF
sysctl --quiet --system
echo "swappiness is now $(cat /proc/sys/vm/swappiness)"

# --- 2. Docker daemon ---------------------------------------------------------
# The compose file sets per-service log limits, but the daemon default applies to anything
# started outside it (one-off `docker run`s during debugging, most obviously). This host has
# already filled its disk once; belt and braces.
log "Writing /etc/docker/daemon.json"
mkdir -p /etc/docker
cat >/etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,
  "userland-proxy": false
}
EOF
# live-restore keeps containers running across a daemon restart; userland-proxy false drops
# one docker-proxy process per published port in favour of pure iptables DNAT.

# --- 3. journald --------------------------------------------------------------
# /var/log/journal had grown to 53 MB on a disk with 2.4 GB free. Cap it rather than relying
# on the deploy script's vacuum.
log "Capping the systemd journal"
mkdir -p /etc/systemd/journald.conf.d
cat >/etc/systemd/journald.conf.d/99-torii.conf <<'EOF'
[Journal]
SystemMaxUse=50M
SystemMaxFileSize=10M
RuntimeMaxUse=16M
EOF
systemctl restart systemd-journald || true
journalctl --vacuum-size=50M >/dev/null 2>&1 || true

# --- 4. Google Cloud Ops Agent (opt-in) --------------------------------------
# ~85 MB of RSS for metrics and log shipping. On a 964 MB host that is the difference
# between fitting in RAM and swapping. Two ways to claw it back:
#
#   --trim-agents  stops the agent outright. Cloud Logging and Cloud Monitoring stop
#                  receiving data from this VM; `docker logs` and this script's journald
#                  config still work, so nothing is lost locally.
#
# Reverse it with:  systemctl enable --now google-cloud-ops-agent
if [[ $TRIM_AGENTS -eq 1 ]]; then
  log "Stopping the Google Cloud Ops Agent (frees ~85 MB RSS)"
  systemctl disable --now google-cloud-ops-agent >/dev/null 2>&1 || true
  systemctl disable --now google-cloud-ops-agent-fluent-bit >/dev/null 2>&1 || true
  systemctl disable --now google-cloud-ops-agent-opentelemetry-collector >/dev/null 2>&1 || true

  # osconfig drives OS Patch Management and inventory. If you do not use either, this is
  # another ~30 MB. Guest agent stays: it owns SSH key provisioning and metadata, and
  # disabling it can lock you out of the instance.
  log "Stopping the OS Config agent (frees ~30 MB RSS)"
  systemctl disable --now google-osconfig-agent >/dev/null 2>&1 || true
else
  echo
  echo "Skipping agent trim. Re-run with --trim-agents to free ~115 MB of RSS"
  echo "(disables Cloud Logging/Monitoring shipping and OS patch inventory)."
fi

# --- 5. Restart Docker --------------------------------------------------------
if [[ $SKIP_DOCKER -eq 1 ]]; then
  echo
  echo "Skipping the Docker restart (--skip-docker). /etc/docker/daemon.json is written but"
  echo "inert until the daemon restarts; the sysctl and journald changes above are already live."
else
  log "Restarting Docker to apply daemon.json"
  systemctl restart docker
  sleep 5
fi

log "Done. Current memory:"
free -m
echo
docker ps --format 'table {{.Names}}\t{{.Status}}'
