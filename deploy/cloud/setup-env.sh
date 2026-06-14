#!/usr/bin/env bash
# Generate production secrets and write/update .env for cloud deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
EXAMPLE="$ROOT/.env.cloud.example"

rand() {
  openssl rand -hex 32
}

hash_password() {
  local pw="$1"
  docker run --rm caddy:2-alpine caddy hash-password --plaintext "$pw"
}

if [[ ! -f "$EXAMPLE" ]]; then
  echo "Missing $EXAMPLE" >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  echo "Backing up existing .env to .env.bak"
  cp "$ENV_FILE" "$ENV_FILE.bak"
fi

cp "$EXAMPLE" "$ENV_FILE"

ADMIN_TOKEN="$(rand)"
POSTGRES_PW="$(rand)"
MINIO_PW="$(rand)"

echo ""
echo "=== Repody cloud setup ==="
read -r -p "App domain (PUBLIC_DOMAIN) [app.example.com]: " PUBLIC_DOMAIN
PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-app.example.com}"
read -r -p "Files domain (FILES_DOMAIN) [files.example.com]: " FILES_DOMAIN
FILES_DOMAIN="${FILES_DOMAIN:-files.example.com}"
read -r -p "Basic auth username [repody]: " BASIC_AUTH_USER
BASIC_AUTH_USER="${BASIC_AUTH_USER:-repody}"
read -r -s -p "Basic auth password (users will enter this in the browser): " BASIC_AUTH_PW
echo ""
read -r -p "vLLM base URL [https://gpu.example.com/v1]: " VLLM_BASE_URL
VLLM_BASE_URL="${VLLM_BASE_URL:-https://gpu.example.com/v1}"
read -r -p "vLLM API key (optional, Enter to skip): " VLLM_API_KEY

BASIC_AUTH_HASH="$(hash_password "$BASIC_AUTH_PW")"

upsert() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

upsert PUBLIC_DOMAIN "$PUBLIC_DOMAIN"
upsert FILES_DOMAIN "$FILES_DOMAIN"
upsert BASIC_AUTH_USER "$BASIC_AUTH_USER"
upsert BASIC_AUTH_HASH "$BASIC_AUTH_HASH"
upsert AUDIT_ADMIN_API_TOKEN "$ADMIN_TOKEN"
upsert POSTGRES_PASSWORD "$POSTGRES_PW"
upsert MINIO_ROOT_PASSWORD "$MINIO_PW"
upsert AUDIT_MINIO_PUBLIC_ENDPOINT "$FILES_DOMAIN"
upsert AUDIT_VLLM_BASE_URL "$VLLM_BASE_URL"
if [[ -n "${VLLM_API_KEY:-}" ]]; then
  upsert AUDIT_VLLM_API_KEY "$VLLM_API_KEY"
fi

# Compose reads POSTGRES_PASSWORD for postgres service if wired; set minio env via compose
upsert MINIO_ROOT_USER "minioadmin"

echo ""
echo "Wrote $ENV_FILE"
echo "  App:   https://${PUBLIC_DOMAIN}"
echo "  Files: https://${FILES_DOMAIN}"
echo "  Share the basic-auth username/password with your users."
echo ""
echo "Next: bash deploy/cloud/bootstrap.sh"
