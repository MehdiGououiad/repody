#!/usr/bin/env bash
# Shared helpers for VPS deploy scripts (Ubuntu 22.04/24.04).
# Compose file chain: deploy/stacks/vps.files (synced from deploy/platform-modules.mjs).
set -euo pipefail

CLOUD_COMPOSE_FILES=()

load_compose_stack() {
  local stack_id="${1:-vps}"
  local lib_dir root list_file line
  lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  root="${REPODY_ROOT:-$(cd "$lib_dir/../.." && pwd)}"
  list_file="${root}/deploy/stacks/${stack_id}.files"
  if [[ ! -f "$list_file" ]]; then
    echo "Missing ${list_file}. Run: pnpm deploy:sync-stacks" >&2
    exit 1
  fi
  CLOUD_COMPOSE_FILES=()
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    CLOUD_COMPOSE_FILES+=(-f "$line")
  done <"$list_file"
}

load_compose_stack "${REPODY_STACK:-vps}"

env_value() {
  local key="$1"
  local file="${2:-.env}"
  grep "^${key}=" "$file" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true
}

inference_mode_from_env() {
  local mode
  mode="$(env_value AUDIT_INFERENCE_MODE)"
  mode="${mode:-docker_model_runner}"
  echo "$mode"
}

cpu_inference_on_vps() {
  local mode
  mode="$(inference_mode_from_env | tr '[:upper:]' '[:lower:]')"
  [[ "$mode" != "vllm" ]]
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    return 0
  fi
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Install Docker Engine + Compose plugin, then re-run." >&2
    exit 1
  fi
  echo "Installing Docker Engine + Compose plugin…" >&2
  apt-get update -qq
  apt-get install -y ca-certificates curl openssl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${VERSION_CODENAME:-$VERSION_ID}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker 2>/dev/null || true
}

ensure_model_plugin() {
  if docker model version >/dev/null 2>&1; then
    return 0
  fi
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Docker Model Runner is required for CPU inference on this host." >&2
    exit 1
  fi
  echo "Installing Docker Model Runner (docker-model-plugin)…" >&2
  apt-get update -qq
  apt-get install -y docker-model-plugin || {
    echo "Could not install docker-model-plugin." >&2
    echo "See https://docs.docker.com/ai/model-runner/get-started/" >&2
    exit 1
  }
  docker model version
}

pull_repody_vlm_model() {
  local lib_dir root
  lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  root="${REPODY_ROOT:-$(cd "$lib_dir/../.." && pwd)}"
  # shellcheck source=/dev/null
  source "${root}/scripts/model-pull-repody-vlm.sh"
}

pull_infra_images() {
  echo "Pulling base images…" >&2
  docker compose --env-file .env "${CLOUD_COMPOSE_FILES[@]}" --profile web pull \
    postgres redis minio hatchet-postgres hatchet-lite hatchet-init caddy 2>/dev/null \
    || docker compose --env-file .env "${CLOUD_COMPOSE_FILES[@]}" --profile web pull
}

app_images_built() {
  docker image inspect repody-api:latest >/dev/null 2>&1 \
    && docker image inspect repody-web:latest >/dev/null 2>&1 \
    && docker image inspect repody-worker:latest >/dev/null 2>&1
}

compose_up_cloud() {
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1

  local build_flag=()
  if [[ "${REPODY_BUILD:-}" == "1" ]] || ! app_images_built; then
    build_flag=(--build)
  fi

  docker compose --env-file .env "${CLOUD_COMPOSE_FILES[@]}" --profile web up -d "${build_flag[@]}" "$@"
}

compose_logs_hint() {
  echo "docker compose --env-file .env ${CLOUD_COMPOSE_FILES[*]} logs -f --tail=100 web api worker"
}

print_platform_urls_vps() {
  local app="${1:-$(env_value PUBLIC_DOMAIN)}"
  local files="${2:-$(env_value FILES_DOMAIN)}"
  app="${app:-app.example.com}"
  files="${files:-files.example.com}"
  echo ""
  echo "════════════════════════════════════════════════════════"
  echo " Platform endpoints"
  echo "────────────────────────────────────────────────────────"
  echo " Web UI         https://${app}"
  echo "                Audit workbench — workflows, runs, uploads"
  echo "                (Caddy basic auth — see BASIC_AUTH_USER in .env)"
  echo " API health     https://${app}/api/v1/healthz"
  echo "                Health check via Next.js proxy"
  echo " File uploads   https://${files}"
  echo "                Browser → MinIO for direct document uploads"
  echo "════════════════════════════════════════════════════════"
  echo ""
}

wait_for_api() {
  local tries="${1:-60}"
  local i
  for ((i = 1; i <= tries; i++)); do
    if docker compose --env-file .env "${CLOUD_COMPOSE_FILES[@]}" exec -T api \
      curl -fsS http://localhost:8000/v1/healthz/live >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
  done
  return 1
}
