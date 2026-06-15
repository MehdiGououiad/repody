#!/usr/bin/env bash
# Ubuntu VPS — first install or full rebuild.
#
#   git clone … && cd repody
#   bash deploy/cloud/deploy.sh
#
# Prerequisites: Ubuntu 22.04/24.04, DNS → this server, ports 80+443 open.
# CPU inference on VPS: 16 GB RAM recommended.
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=deploy/cloud/lib.sh
source "$ROOT/deploy/cloud/lib.sh"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Run this on your Ubuntu VPS (not Windows/macOS)." >&2
  exit 1
fi

if [[ "${EUID:-0}" -ne 0 ]] && ! groups 2>/dev/null | grep -qw docker; then
  echo "Run as root or a user in the docker group:" >&2
  echo "  sudo bash deploy/cloud/deploy.sh" >&2
  exit 1
fi

ensure_docker

if [[ ! -f .env ]]; then
  echo ""
  echo "No .env — starting setup…"
  bash "$ROOT/deploy/cloud/setup-env.sh"
fi

pull_infra_images

model_pid=""
if cpu_inference_on_vps; then
  ensure_model_plugin
  pull_repody_vlm_model &
  model_pid=$!
fi

export REPODY_BUILD=1
echo ""
echo "Building and starting Repody (first deploy builds app images; later updates use bootstrap.sh)…"
compose_up_cloud

if [[ -n "$model_pid" ]]; then
  wait "$model_pid" || true
fi

PUBLIC_DOMAIN="$(env_value PUBLIC_DOMAIN)"
print_platform_urls_vps "$PUBLIC_DOMAIN" "$(env_value FILES_DOMAIN)"
echo ""
echo "════════════════════════════════════════════════════════"
echo "  Waiting for API…"
if wait_for_api 36; then
  echo "  API is up."
else
  echo "  API still starting — check logs if this persists."
fi
echo ""
echo "  curl -s https://${PUBLIC_DOMAIN:-your-domain}/api/v1/healthz"
echo "  $(compose_logs_hint)"
echo "════════════════════════════════════════════════════════"
