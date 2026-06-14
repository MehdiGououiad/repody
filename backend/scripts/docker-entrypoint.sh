#!/bin/sh
set -e
cd /app
if [ -z "${HATCHET_CLIENT_TOKEN:-}" ] && [ -f /shared/hatchet.token ]; then
  export HATCHET_CLIENT_TOKEN="$(cat /shared/hatchet.token)"
fi
if [ "${AUDIT_RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ] && [ -f alembic.ini ]; then
  echo "Running database migrations…"
  python /app/scripts/bootstrap_migrations.py
fi
exec "$@"
