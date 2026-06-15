#!/usr/bin/env bash
# Ubuntu VPS deploy smoke test — run inside ubuntu:24.04 with repo at /repody and docker.sock mounted.
set -euo pipefail
cd /repody

export DEBIAN_FRONTEND=noninteractive
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl openssl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce-cli docker-compose-plugin
fi

chmod +x deploy/cloud/*.sh scripts/deploy/*.sh 2>/dev/null || true
rm -f .env

REPODY_NONINTERACTIVE=1 \
  PUBLIC_DOMAIN=localhost \
  FILES_DOMAIN=files.localhost \
  BASIC_AUTH_PW=repody-test-pass \
  bash deploy/cloud/setup-env.sh

# shellcheck source=deploy/cloud/lib.sh
source deploy/cloud/lib.sh

echo "=== .env secrets ==="
grep -E '^(BASIC_AUTH_HASH|AUDIT_INFERENCE_MODE)=' .env

docker compose --env-file .env "${CLOUD_COMPOSE_FILES[@]}" config --quiet
echo "compose config: OK"

bash deploy/cloud/deploy.sh

echo "=== containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | head -15

echo "=== api health ==="
docker compose --env-file .env "${CLOUD_COMPOSE_FILES[@]}" \
  exec -T api curl -fsS http://localhost:8000/v1/healthz/live
echo "healthz/live: OK"
