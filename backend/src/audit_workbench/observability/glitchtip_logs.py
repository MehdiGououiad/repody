"""Forward selected structlog events to GlitchTip (Sentry logs UI)."""

from __future__ import annotations

import logging
import os
from typing import Any

import structlog

_LEVEL_RANK: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

_SKIP_KEYS = frozenset({"event", "body", "_record", "_from_structlog"})


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def glitchtip_logs_enabled() -> bool:
    return bool(os.getenv("SENTRY_DSN", "").strip()) and _env_truthy("SENTRY_ENABLE_LOGS")


def _min_forward_level() -> int:
    raw = os.getenv("SENTRY_LOG_LEVEL", "WARNING").strip().upper()
    return getattr(logging, raw, logging.WARNING)


def should_forward_log_level(level_name: str) -> bool:
    if not glitchtip_logs_enabled():
        return False
    return _LEVEL_RANK.get(level_name, logging.INFO) >= _min_forward_level()


def _serialize_attributes(event_dict: dict[str, Any]) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for key, value in event_dict.items():
        if key in _SKIP_KEYS:
            continue
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            attrs[key] = value
        else:
            attrs[key] = str(value)
    return attrs


def structlog_glitchtip_processor(
    _logger: object, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Side-effect processor: WARNING+ on API when SENTRY_ENABLE_LOGS is set."""
    if not should_forward_log_level(method_name):
        return event_dict

    try:
        from sentry_sdk import logger as sentry_logger

        message = event_dict.get("event") or event_dict.get("body") or method_name
        attributes = _serialize_attributes(event_dict)
        log_fn = getattr(sentry_logger, method_name, sentry_logger.warning)
        log_fn(str(message), **attributes)
    except Exception:
        pass

    return event_dict
