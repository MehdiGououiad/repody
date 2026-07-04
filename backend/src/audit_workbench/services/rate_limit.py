"""Redis-backed rate limiting via the `limits` library (moving window)."""

from __future__ import annotations

import structlog
from limits import RateLimitItem, parse
from limits.aio.storage import MemoryStorage, RedisStorage
from limits.aio.strategies import MovingWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from audit_workbench.settings import Settings, get_settings

log = structlog.get_logger(__name__)

_limiter: MovingWindowRateLimiter | None = None
_storage: MemoryStorage | RedisStorage | None = None
_GLOBAL_HTTP_LIMIT = parse("300 per minute")


class RunRateLimitExceeded(Exception):
    def __init__(self, *, scope: str, limit: int, window_seconds: int) -> None:
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(f"Rate limit exceeded ({scope}): max {limit} runs per {window_seconds}s.")


def clear_rate_limiter_cache() -> None:
    """Reset cached limiter (tests)."""
    global _limiter, _storage
    _limiter = None
    _storage = None


def _window_limit(settings: Settings, max_runs: int) -> RateLimitItem:
    window = max(1, settings.rate_limit_window_seconds)
    return parse(f"{max_runs} per {window} second")


async def _get_limiter() -> MovingWindowRateLimiter:
    global _limiter, _storage
    if _limiter is not None:
        return _limiter
    settings = get_settings()
    try:
        _storage = RedisStorage(settings.redis_url)
    except Exception as exc:
        log.warning(
            "rate_limit_redis_storage_failed",
            event_domain="rate_limit",
            error_type=type(exc).__name__,
            error_message=repr(exc),
        )
        _storage = MemoryStorage()
    _limiter = MovingWindowRateLimiter(_storage)
    return _limiter


def _allow_on_redis_error(settings: Settings) -> bool:
    """Return True to allow the request when Redis rate-limit storage fails."""
    return not settings.rate_limit_fail_closed


async def check_run_rate_limits(
    *,
    workflow_id: str,
    source: str,
    client_key: str | None = None,
) -> None:
    """
    Enforce per-workflow and per-client run creation limits.

    client_key should be API key hash or client IP for deployed runs.
    """
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    limiter = await _get_limiter()
    window = max(1, settings.rate_limit_window_seconds)
    wf_key = f"audit:rl:wf:{workflow_id}:{source}"
    wf_limit = _window_limit(settings, settings.rate_limit_runs_per_workflow)

    try:
        allowed = await limiter.hit(wf_limit, wf_key)
    except Exception as exc:
        log.warning(
            "rate_limit_redis_unavailable",
            event_domain="rate_limit",
            error_type=type(exc).__name__,
            error_message=repr(exc),
        )
        if not _allow_on_redis_error(settings):
            raise RunRateLimitExceeded(
                scope="redis",
                limit=0,
                window_seconds=window,
            ) from exc
        return

    if not allowed:
        log.warning(
            "rate_limit_workflow_exceeded",
            event_domain="rate_limit",
            workflow_id=workflow_id,
            source=source,
            limit=settings.rate_limit_runs_per_workflow,
        )
        raise RunRateLimitExceeded(
            scope=f"workflow:{workflow_id}",
            limit=settings.rate_limit_runs_per_workflow,
            window_seconds=window,
        )

    if not client_key:
        return

    client_redis_key = f"audit:rl:client:{client_key}"
    client_limit = _window_limit(settings, settings.rate_limit_runs_per_client)
    try:
        allowed = await limiter.hit(client_limit, client_redis_key)
    except Exception as exc:
        log.warning(
            "rate_limit_redis_unavailable",
            event_domain="rate_limit",
            error_type=type(exc).__name__,
            error_message=repr(exc),
        )
        if not _allow_on_redis_error(settings):
            raise RunRateLimitExceeded(
                scope="redis",
                limit=0,
                window_seconds=window,
            ) from exc
        return

    if not allowed:
        log.warning(
            "rate_limit_client_exceeded",
            event_domain="rate_limit",
            client_key=client_key,
            limit=settings.rate_limit_runs_per_client,
        )
        raise RunRateLimitExceeded(
            scope="client",
            limit=settings.rate_limit_runs_per_client,
            window_seconds=window,
        )


async def check_global_http_rate_limit(client_ip: str) -> bool:
    """Return True when the request is allowed under the global HTTP limit."""
    settings = get_settings()
    limiter = await _get_limiter()
    try:
        return await limiter.hit(_GLOBAL_HTTP_LIMIT, f"audit:rl:http:{client_ip}")
    except Exception as exc:
        log.warning(
            "rate_limit_redis_unavailable",
            event_domain="rate_limit",
            error_type=type(exc).__name__,
            error_message=repr(exc),
        )
        return _allow_on_redis_error(settings)


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Global per-IP HTTP rate limit (300/min) using the same `limits` storage."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not get_settings().rate_limit_enabled:
            return await call_next(request)
        if request.url.path == "/v1/healthz":
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        if not await check_global_http_rate_limit(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )
        return await call_next(request)
