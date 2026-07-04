"""Shared observability startup for API and Taskiq workers."""

from __future__ import annotations

import os

from audit_workbench.observability.bugsink import init_bugsink
from audit_workbench.observability.logging import configure_logging
from audit_workbench.observability.tracing import instrument_dependencies, setup_tracing
from audit_workbench.settings import Settings, get_settings


def init_observability(settings: Settings | None = None) -> Settings:
    """Configure structured logging and optional OpenTelemetry for this process."""
    resolved = settings or get_settings()
    configure_logging(resolved)
    init_bugsink(
        service_name=os.getenv("AUDIT_OTEL_SERVICE_NAME")
        or os.getenv("BUGSINK_SERVER_NAME")
        or resolved.otel_service_name
    )
    setup_tracing(resolved)
    instrument_dependencies(resolved)
    return resolved
