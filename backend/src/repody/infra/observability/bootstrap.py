"""Shared observability startup for API and Taskiq workers."""

from __future__ import annotations

import os

from repody.infra.observability.bugsink import init_bugsink
from repody.infra.observability.logging import configure_logging, service_name
from repody.settings import Settings, get_settings


def init_observability(settings: Settings | None = None) -> Settings:
    """Configure structured logging and error tracking (tracing is the OTEL agent's job)."""
    resolved = settings or get_settings()
    configure_logging(resolved)
    init_bugsink(service_name=os.getenv("BUGSINK_SERVER_NAME") or service_name())
    return resolved
