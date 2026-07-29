"""Request-scoped logging context (OpenTelemetry-friendly)."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Any

import structlog


def bind_log_context(**fields: Any) -> None:
    structlog.contextvars.bind_contextvars(**fields)


def clear_log_context() -> None:
    structlog.contextvars.clear_contextvars()


def new_request_id() -> str:
    return uuid.uuid4().hex


@contextmanager
def log_context(**fields: Any):
    bind_log_context(**fields)
    try:
        yield
    finally:
        clear_log_context()
