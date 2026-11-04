#!/bin/sh
set -e
cd /app
if [ "${AUDIT_RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  alembic upgrade head
fi
# OpenTelemetry zero-code agent when OTEL_SDK_DISABLED=false; it reads OTEL_SERVICE_NAME,
# OTEL_EXPORTER_OTLP_ENDPOINT, ... (https://opentelemetry.io/docs/zero-code/python/).
if [ "${OTEL_SDK_DISABLED:-true}" = "false" ]; then
  set -- opentelemetry-instrument "$@"
fi
exec "$@"
