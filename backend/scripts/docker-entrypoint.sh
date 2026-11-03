#!/bin/sh
set -e
cd /app
if [ "${AUDIT_RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ] && [ -f alembic.ini ]; then
  echo "Running database migrations…"
  python /app/scripts/bootstrap_migrations.py
fi
# OpenTelemetry agent (zero-code instrumentation) when OTEL_SDK_DISABLED=false; it reads
# OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, ... (https://opentelemetry.io/docs/zero-code/python/).
if [ "${OTEL_SDK_DISABLED:-true}" = "false" ] && command -v opentelemetry-instrument >/dev/null 2>&1; then
  set -- opentelemetry-instrument "$@"
fi
exec "$@"
