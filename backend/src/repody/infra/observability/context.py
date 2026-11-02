"""Request-scoped logging context (OpenTelemetry-friendly)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import structlog


def bind_log_context(**fields: Any) -> None:
    structlog.contextvars.bind_contextvars(**fields)


def clear_log_context() -> None:
    structlog.contextvars.clear_contextvars()


@contextmanager
def log_context(**fields: Any):
    bind_log_context(**fields)
    try:
        yield
    finally:
        clear_log_context()
