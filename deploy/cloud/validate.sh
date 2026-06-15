#!/usr/bin/env bash
# Quick validation for VPS deploy scripts (no Docker required).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/deploy/stacks/vps.files" ]]; then
  echo "Missing deploy/stacks/vps.files — run: pnpm deploy:sync-stacks" >&2
  exit 1
fi

# shellcheck source=deploy/cloud/lib.sh
source "$ROOT/deploy/cloud/lib.sh"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

upsert_test() {
  local key="$1" val="$2"
  if [[ "$key" == "BASIC_AUTH_HASH" ]]; then
    val="$(printf '%s' "$val" | sed 's/\$/$$/g')"
  fi
  grep -v "^${key}=" "$tmp" 2>/dev/null >"${tmp}.new" || : >"${tmp}.new"
  printf '%s=%s\n' "$key" "$val" >>"${tmp}.new"
  mv "${tmp}.new" "$tmp"
}

upsert_test BASIC_AUTH_HASH '$2a$14$newhash$value/with/slashes'

if ! grep -Fxq 'BASIC_AUTH_HASH=$$2a$$14$$newhash$$value/with/slashes' "$tmp"; then
  echo "FAIL: upsert did not preserve bcrypt hash" >&2
  exit 1
fi

for script in deploy/cloud/lib.sh deploy/cloud/deploy.sh deploy/cloud/bootstrap.sh deploy/cloud/setup-env.sh; do
  bash -n "$script"
done

echo "PASS: VPS deploy scripts"
