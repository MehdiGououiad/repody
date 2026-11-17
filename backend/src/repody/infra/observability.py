"""Logging (structlog over stdlib logging) and error reporting (Sentry SDK, e.g. Bugsink).

Tracing is the OpenTelemetry agent's job (``opentelemetry-instrument``, configured by OTEL_*).
Hatchet's instrumentor is not one of the agent's, so it is started here when tracing is on: a
run's trigger in the API and its task on the worker then share one trace.
Error reporting turns on when SENTRY_DSN is set; the SDK enables its FastAPI, Starlette and
logging integrations by default.
"""

import logging
import os

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
    # JSON (Loki) gets structured tracebacks; the console renderer formats exceptions itself
    # (structlog warns against format_exc_info in front of it).
    renderers: list[structlog.types.Processor] = (
        [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer()]
        if settings.log_json
        else [structlog.dev.ConsoleRenderer()]
    )
    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *renderers],
        )
    )
    logging.basicConfig(handlers=[handler], level=level, force=True)
    # Uvicorn gives its loggers their own text handlers; send them to the root handler instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, _QuietHealthChecks) for f in access.filters):
        access.addFilter(_QuietHealthChecks())
    # Errors only: tracing is the OpenTelemetry agent's. Leaving traces_sample_rate unset is
    # what turns Sentry tracing off (any value, even 0, enables it).
    # No local variables in reports: on the extraction path they hold uploaded files, page images
    # and extracted values (clients' documents). Tracebacks and messages are enough.
    sentry_sdk.init(environment=settings.deployment_environment, include_local_variables=False)
    if os.environ.get("OTEL_SDK_DISABLED", "true") == "false":
        _trace_hatchet()


class _QuietHealthChecks(logging.Filter):
    """Drops the access lines of answered health checks (Docker asks every 15 seconds): they
    were most of the log. A failed one is still written."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn's access record: (client, method, path, HTTP version, status).
        args = record.args
        if isinstance(args, tuple) and len(args) == 5:
            path, status = str(args[2]), args[4]
            if path.startswith("/v1/healthz") and isinstance(status, int) and status < 400:
                return False
        return True


def _trace_hatchet() -> None:
    # The `otel` extra, installed wherever the agent runs.
    from hatchet_sdk.opentelemetry.instrumentor import HatchetInstrumentor

    # Spans go to the agent's tracer provider (our collector), not to Hatchet's engine.
    HatchetInstrumentor(enable_hatchet_otel_collector=False).instrument()
