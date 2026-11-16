#!/bin/sh
set -e
if [ "${AUDIT_RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  alembic upgrade head
fi
# The Hatchet API token from a file when one is given (deploy/vps: the hatchet-token service).
if [ -n "${HATCHET_CLIENT_TOKEN_FILE:-}" ]; then
  HATCHET_CLIENT_TOKEN="$(cat "$HATCHET_CLIENT_TOKEN_FILE")"
  export HATCHET_CLIENT_TOKEN
fi
# OpenTelemetry zero-code agent when OTEL_SDK_DISABLED=false; it reads OTEL_SERVICE_NAME,
# OTEL_EXPORTER_OTLP_ENDPOINT, ... (https://opentelemetry.io/docs/zero-code/python/).
if [ "${OTEL_SDK_DISABLED:-true}" = "false" ]; then
  set -- opentelemetry-instrument "$@"
fi
exec "$@"
