"""HTTP middleware for structured access logs (OTEL-friendly fields)."""

from __future__ import annotations

import time
from typing import Any

import structlog
from asgi_correlation_id.context import correlation_id
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from audit_workbench.observability.context import bind_log_context, clear_log_context
from audit_workbench.settings import get_settings

log = structlog.get_logger(__name__)


def _otel_trace_fields() -> dict[str, str]:
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if not span.is_recording():
            return {}
        ctx = span.get_span_context()
        if not ctx.is_valid:
            return {}
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        }
    except ImportError:
        return {}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one structured log per HTTP request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        request_id = correlation_id.get() or request.headers.get("x-request-id")
        client_host = request.client.host if request.client else None

        clear_log_context()
        bind_log_context(
            request_id=request_id,
            correlation_id=request_id,
            http_request_method=request.method,
            url_path=request.url.path,
            client_address=client_host,
            service_name=settings.otel_service_name,
            deployment_environment=settings.deployment_environment,
            **_otel_trace_fields(),
        )

        started = time.perf_counter()
        status_code = 500
        failed = False
        try:
            response = await call_next(request)
            status_code = response.status_code
            if request_id:
                response.headers.setdefault("X-Request-ID", request_id)
            return response
        except Exception:
            failed = True
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            fields: dict[str, Any] = {
                "event_domain": "http",
                "http_response_status_code": status_code,
                "duration_ms": duration_ms,
            }
            if failed or status_code >= 500:
                log.error("http_request_completed", **fields)
            else:
                log.info("http_request_completed", **fields)
            clear_log_context()
