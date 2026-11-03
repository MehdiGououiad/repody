"""Tracer for Repody's own spans.

The OpenTelemetry agent (`opentelemetry-instrument`, run by scripts/docker-entrypoint.sh when
OTEL_SDK_DISABLED=false) configures the SDK and instruments FastAPI, httpx, SQLAlchemy and
logging from OTEL_* env. Without it, these spans are no-ops.
"""

from __future__ import annotations

from opentelemetry import trace

tracer = trace.get_tracer("repody")
