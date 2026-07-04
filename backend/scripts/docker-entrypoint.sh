#!/bin/sh
set -e
cd /app
if [ "${AUDIT_RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ] && [ -f alembic.ini ]; then
  echo "Running database migrations…"
  python /app/scripts/bootstrap_migrations.py
fi
exec "$@"
