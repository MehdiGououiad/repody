"""Production structlog configuration aligned with OpenTelemetry log conventions."""

from __future__ import annotations

import logging
import sys

import structlog

from audit_workbench.settings import Settings

_SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private_key",
)


def _should_redact_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def _redact_sensitive_fields(
    _logger: object,
    _method: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    for key, value in list(event_dict.items()):
        if key in {"_record", "_from_structlog"}:
            continue
        if _should_redact_key(key) and value is not None:
            event_dict[key] = "***REDACTED***"
    return event_dict


def _add_service_context(settings: Settings) -> structlog.types.Processor:
    def processor(
        _logger: object,
        _method: str,
        event_dict: structlog.types.EventDict,
    ) -> structlog.types.EventDict:
        event_dict.setdefault("service.name", settings.otel_service_name)
        event_dict.setdefault("deployment.environment", settings.deployment_environment)
        return event_dict

    return processor


def _add_otel_trace_context() -> structlog.types.Processor:
    def processor(
        _logger: object,
        _method: str,
        event_dict: structlog.types.EventDict,
    ) -> structlog.types.EventDict:
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            if span.is_recording():
                ctx = span.get_span_context()
                if ctx.is_valid:
                    event_dict.setdefault("trace_id", format(ctx.trace_id, "032x"))
                    event_dict.setdefault("span_id", format(ctx.span_id, "016x"))
        except ImportError:
            pass
        return event_dict

    return processor


def _rename_event_to_body() -> structlog.types.Processor:
    """Map structlog `event` to OTEL-style `body` while keeping `event` for compatibility."""

    def processor(
        _logger: object,
        _method: str,
        event_dict: structlog.types.EventDict,
    ) -> structlog.types.EventDict:
        message = event_dict.get("event")
        if isinstance(message, str):
            event_dict.setdefault("body", message)
        return event_dict

    return processor


def configure_logging(settings: Settings) -> None:
    """Configure structlog for dev (console) or prod (JSON, OTEL-friendly fields)."""
    log_level = logging.DEBUG if settings.debug else logging.INFO

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        _add_service_context(settings),
        _add_otel_trace_context(),
        _redact_sensitive_fields,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _rename_event_to_body(),
    ]

    if settings.log_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.UnicodeDecoder(),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    # Route stdlib loggers through structlog for consistent formatting.
    for name in ("uvicorn", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

    # RequestLoggingMiddleware emits structured access logs; skip uvicorn duplicates.
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = False
    uvicorn_access.disabled = True

    structlog.get_logger(__name__).info(
        "logging_configured",
        event_domain="platform",
        log_format="json" if settings.log_json else "console",
        log_level=logging.getLevelName(log_level),
    )
