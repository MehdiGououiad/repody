#!/usr/bin/env bash
# Fast update after git pull — rebuild only when REPODY_BUILD=1.
#
#   git pull && bash deploy/cloud/bootstrap.sh
#   git pull && REPODY_BUILD=1 bash deploy/cloud/bootstrap.sh   # after code changes
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=deploy/cloud/lib.sh
source "$ROOT/deploy/cloud/lib.sh"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Run this on your Ubuntu VPS." >&2
  exit 1
fi

ensure_docker

if [[ ! -f .env ]]; then
  echo "No .env found. Run: bash deploy/cloud/deploy.sh" >&2
  exit 1
fi

if cpu_inference_on_vps; then
  ensure_model_plugin
  pull_repody_vlm_model
fi

pull_infra_images

echo "Starting Repody…"
compose_up_cloud

PUBLIC_DOMAIN="$(env_value PUBLIC_DOMAIN)"
echo ""
echo "Done. https://${PUBLIC_DOMAIN}"
echo "$(compose_logs_hint)"
