"""Bugsink error tracking via the Sentry SDK.

https://www.bugsink.com/docs/sdk-recommendations/
https://docs.sentry.io/platforms/python/integrations/fastapi/
https://docs.sentry.io/platforms/python/integrations/logging/
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

if TYPE_CHECKING:
    from sentry_sdk.types import Breadcrumb, BreadcrumbHint, Event, Hint
_initialized = False

_EVENT_DICT_SKIP = frozenset(
    {"event", "exc_info", "exception", "stack", "stack_info", "_record", "_from_structlog"}
)


def _json_safe(value: object) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_json_safe(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _json_safe(item) for key, item in value.items())
    return False


def _structlog_event_name(hint: Hint | BreadcrumbHint) -> str | None:
    record = hint.get("log_record")
    message = getattr(record, "msg", None)
    if not isinstance(message, dict):
        return None
    event_name = message.get("event")
    if isinstance(event_name, str) and event_name:
        return event_name
    return None


def _before_send(event: Event, hint: Hint) -> Event:
    """Use the structlog event name as the Sentry message and keep its fields."""
    record = hint.get("log_record")
    message = getattr(record, "msg", None)
    event_name = _structlog_event_name(hint)
    logentry = event.get("logentry")
    if event_name and isinstance(logentry, dict):
        logentry["message"] = event_name
        logentry["formatted"] = event_name
    if isinstance(message, dict):
        extra = event.get("extra")
        if not isinstance(extra, dict):
            extra = {}
            event["extra"] = extra
        for key, value in message.items():
            if key in _EVENT_DICT_SKIP or key.startswith("_"):
                continue
            if key not in extra and _json_safe(value):
                extra[key] = value
    return event


def _before_breadcrumb(crumb: Breadcrumb, hint: BreadcrumbHint) -> Breadcrumb:
    event_name = _structlog_event_name(hint)
    if event_name:
        crumb["message"] = event_name
    return crumb


def bugsink_enabled() -> bool:
    return bool(os.getenv("BUGSINK_DSN", "").strip())


def init_bugsink(service_name: str | None = None) -> None:
    """Init once, as early as possible (before FastAPI()/ASGI serve)."""
    global _initialized
    if _initialized:
        return
    dsn = os.getenv("BUGSINK_DSN", "").strip()
    if not dsn:
        return
    # Bugsink stores error events only. Traces, sessions, client reports, and
    # Sentry's logs product stay off (capture_sentry_logs=False).
    # Bugsink's Python setup sets send_default_pii and max_request_body_size="always".
    # FastAPI requires both StarletteIntegration and FastApiIntegration when set explicitly.
    # LoggingIntegration turns stdlib ERROR records into events. structlog reaches
    # that path through LoggerFactory; before_send keeps the event name as the message.
    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("BUGSINK_ENVIRONMENT")
        or os.getenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "development"),
        release=os.getenv("BUGSINK_RELEASE", "").strip() or None,
        server_name=service_name,
        send_default_pii=True,
        max_request_body_size="always",
        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
        before_send=_before_send,
        before_breadcrumb=_before_breadcrumb,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
                capture_sentry_logs=False,
            ),
        ],
    )
    _initialized = True
