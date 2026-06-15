#!/usr/bin/env bash
# Generate production secrets and write/update .env for cloud deploy.
# Variable reference: deploy/ENV.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
EXAMPLE="$ROOT/.env.cloud.example"

# shellcheck source=deploy/cloud/lib.sh
source "$ROOT/deploy/cloud/lib.sh"

rand() {
  openssl rand -hex 32
}

hash_password() {
  local pw="$1"
  if ! docker info >/dev/null 2>&1; then
    ensure_docker
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not reachable (required to hash basic-auth password)." >&2
    exit 1
  fi
  docker run --rm caddy:2.10-alpine caddy hash-password --plaintext "$pw"
}

# Safe for bcrypt hashes ($) and docker-compose .env interpolation.
upsert() {
  local key="$1" val="$2"
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$ENV_FILE" ]]; then
    grep -v "^${key}=" "$ENV_FILE" >"$tmp" || true
  else
    : >"$tmp"
  fi
  # Compose treats $ as variable refs in .env — escape for hash values.
  if [[ "$key" == "BASIC_AUTH_HASH" ]]; then
    val="$(printf '%s' "$val" | sed 's/\$/$$/g')"
  fi
  printf '%s=%s\n' "$key" "$val" >>"$tmp"
  mv "$tmp" "$ENV_FILE"
}

if [[ ! -f "$EXAMPLE" ]]; then
  echo "Missing $EXAMPLE" >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y openssl
fi

if [[ -f "$ENV_FILE" ]]; then
  echo "Backing up existing .env to .env.bak"
  cp "$ENV_FILE" "$ENV_FILE.bak"
fi

cp "$EXAMPLE" "$ENV_FILE"

ADMIN_TOKEN="$(rand)"
POSTGRES_PW="$(rand)"
MINIO_PW="$(rand)"

if [[ "${REPODY_NONINTERACTIVE:-}" == "1" ]]; then
  PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-app.example.com}"
  FILES_DOMAIN="${FILES_DOMAIN:-files.example.com}"
  BASIC_AUTH_USER="${BASIC_AUTH_USER:-repody}"
  BASIC_AUTH_PW="${BASIC_AUTH_PW:?Set BASIC_AUTH_PW for non-interactive setup}"
  INFERENCE_CHOICE="${INFERENCE_CHOICE:-1}"
  VLLM_BASE_URL="${VLLM_BASE_URL:-https://gpu.example.com/v1}"
  VLLM_API_KEY="${VLLM_API_KEY:-}"
else
  echo ""
  echo "=== Repody VPS setup ==="
  echo "Point DNS A records to this server (app + files hostnames) before deploy finishes."
  echo ""
  read -r -p "App domain (PUBLIC_DOMAIN) [app.example.com]: " PUBLIC_DOMAIN
  PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-app.example.com}"
  read -r -p "Files domain (FILES_DOMAIN) [files.example.com]: " FILES_DOMAIN
  FILES_DOMAIN="${FILES_DOMAIN:-files.example.com}"
  read -r -p "Basic auth username [repody]: " BASIC_AUTH_USER
  BASIC_AUTH_USER="${BASIC_AUTH_USER:-repody}"
  read -r -s -p "Basic auth password (users enter this in the browser): " BASIC_AUTH_PW
  echo ""
  echo ""
  echo "Inference:"
  echo "  1) CPU on this VPS — all-in-one (~16 GB RAM)"
  echo "  2) External GPU / vLLM — platform only on this VPS"
  read -r -p "Choice [1]: " INFERENCE_CHOICE
  INFERENCE_CHOICE="${INFERENCE_CHOICE:-1}"
  VLLM_BASE_URL=""
  VLLM_API_KEY=""
  if [[ "$INFERENCE_CHOICE" == "2" ]]; then
    read -r -p "vLLM base URL [https://gpu.example.com/v1]: " VLLM_BASE_URL
    VLLM_BASE_URL="${VLLM_BASE_URL:-https://gpu.example.com/v1}"
    read -r -p "vLLM API key (optional, Enter to skip): " VLLM_API_KEY
  fi
fi

BASIC_AUTH_HASH="$(hash_password "$BASIC_AUTH_PW")"

upsert PUBLIC_DOMAIN "$PUBLIC_DOMAIN"
upsert FILES_DOMAIN "$FILES_DOMAIN"
upsert BASIC_AUTH_USER "$BASIC_AUTH_USER"
upsert BASIC_AUTH_HASH "$BASIC_AUTH_HASH"
upsert AUDIT_ADMIN_API_TOKEN "$ADMIN_TOKEN"
upsert POSTGRES_PASSWORD "$POSTGRES_PW"
upsert MINIO_ROOT_PASSWORD "$MINIO_PW"
upsert AUDIT_MINIO_PUBLIC_ENDPOINT "$FILES_DOMAIN"
upsert MINIO_ROOT_USER "minioadmin"

if [[ "$INFERENCE_CHOICE" == "2" ]]; then
  upsert AUDIT_INFERENCE_MODE "vllm"
  upsert AUDIT_VLLM_BASE_URL "$VLLM_BASE_URL"
  upsert AUDIT_REPODY_VLM_WARMUP_ON_START "false"
  upsert AUDIT_REPODY_VLM_TIMEOUT_SECONDS "900"
  if [[ -n "${VLLM_API_KEY:-}" ]]; then
    upsert AUDIT_VLLM_API_KEY "$VLLM_API_KEY"
  fi
else
  upsert AUDIT_INFERENCE_MODE "docker_model_runner"
  upsert AUDIT_REPODY_VLM_WARMUP_ON_START "true"
  upsert AUDIT_REPODY_VLM_TIMEOUT_SECONDS "600"
fi

echo ""
echo "Wrote $ENV_FILE"
echo "  App:   https://${PUBLIC_DOMAIN}"
echo "  Files: https://${FILES_DOMAIN}"
if [[ "$INFERENCE_CHOICE" == "1" ]]; then
  echo "  Inference: CPU on this VPS (Docker Model Runner)"
else
  echo "  Inference: external vLLM at ${VLLM_BASE_URL}"
fi
echo ""
echo "Next: bash deploy/cloud/deploy.sh"
