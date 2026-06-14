#!/usr/bin/env bash
# One-time cloud server bootstrap (Ubuntu 22.04/24.04). Run as root or with sudo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker…"
  apt-get update -qq
  apt-get install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${VERSION_CODENAME:-$VERSION_ID}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
fi

if [[ ! -f .env ]]; then
  echo "No .env found. Run: bash deploy/cloud/setup-env.sh"
  exit 1
fi

# Load secrets for compose substitution (hash values stay in the file; do not source .env)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

COMPOSE_FILES="-f compose.yaml -f compose.cpu.yaml -f compose.prod.yaml -f compose.public.yaml -f compose.cloud.yaml"

echo "Building and starting Repody (cloud)…"
docker compose --env-file .env $COMPOSE_FILES --profile web up -d --build

PUBLIC_DOMAIN="$(grep '^PUBLIC_DOMAIN=' .env | cut -d= -f2- | tr -d '\r')"
echo ""
echo "Deployment started. Wait ~2 minutes, then open: https://${PUBLIC_DOMAIN}"
echo "Logs: docker compose --env-file .env $COMPOSE_FILES logs -f --tail=100 web api worker"
