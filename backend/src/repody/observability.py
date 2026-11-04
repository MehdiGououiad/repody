"""Logging (structlog over stdlib logging) and error reporting (Sentry SDK, e.g. Bugsink).

Tracing is the OpenTelemetry agent's job (``opentelemetry-instrument``, configured by OTEL_*).
Error reporting turns on when SENTRY_DSN is set; the SDK enables its FastAPI, Starlette and
logging integrations by default.
"""

from __future__ import annotations

import logging

import sentry_sdk
import structlog

from repody.settings import get_settings


def setup() -> None:
    settings = get_settings()
    level = logging.DEBUG if settings.debug else logging.INFO
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )
    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.format_exc_info,
                renderer,
            ],
        )
    )
    logging.basicConfig(handlers=[handler], level=level, force=True)
    sentry_sdk.init(environment=settings.deployment_environment, traces_sample_rate=0)
