from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from audit_workbench.settings import Settings

log = structlog.get_logger()
_tracer: Any | None = None
_instrumented = False


def setup_tracing(settings: Settings) -> None:
    global _tracer
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        log.warning("otel_packages_missing", hint="pip install audit-workbench[otel]")
        return

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(settings.otel_service_name)
    log.info("otel_tracing_enabled", endpoint=settings.otel_exporter_endpoint)


def instrument_dependencies(settings: Settings) -> None:
    """Instrument httpx and SQLAlchemy when OTEL is enabled."""
    global _instrumented
    if not settings.otel_enabled or _instrumented:
        return

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except ImportError:
        log.warning("otel_httpx_missing", hint="pip install opentelemetry-instrumentation-httpx")
    else:
        HTTPXClientInstrumentor().instrument()
        log.info("otel_httpx_instrumented")

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        from audit_workbench.db.base import engine

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        log.info("otel_sqlalchemy_instrumented")
    except ImportError:
        log.warning(
            "otel_sqlalchemy_missing",
            hint="pip install opentelemetry-instrumentation-sqlalchemy",
        )
    except Exception as exc:
        log.warning("otel_sqlalchemy_failed", error=repr(exc))

    try:
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
    except ImportError:
        log.warning(
            "otel_logging_missing",
            hint="pip install audit-workbench[otel] for log trace correlation",
        )
    else:
        LoggingInstrumentor().instrument(set_logging_format=False)
        log.info("otel_logging_instrumented")

    _instrumented = True


def instrument_fastapi(app: Any, settings: Settings) -> None:
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        return
    FastAPIInstrumentor.instrument_app(app)
    instrument_dependencies(settings)


@asynccontextmanager
async def start_span(name: str, attributes: dict[str, Any] | None = None):
    if _tracer is None:
        yield
        return
    with _tracer.start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            span.set_attribute(key, value)
        yield
