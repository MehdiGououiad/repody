"""Redis-backed rate limiting via the `limits` library (moving window)."""

from __future__ import annotations

import structlog
from limits import RateLimitItem, parse
from limits.aio.storage import MemoryStorage, RedisStorage
from limits.aio.strategies import MovingWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from audit_workbench.platform.contracts.result import AppError, ErrorCode, Result
from audit_workbench.settings import Settings, get_settings

log = structlog.get_logger(__name__)

_limiter: MovingWindowRateLimiter | None = None
_storage: MemoryStorage | RedisStorage | None = None
_http_limit_cache: tuple[int, RateLimitItem] | None = None


def clear_rate_limiter_cache() -> None:
    """Reset cached limiter (tests)."""
    global _limiter, _storage, _http_limit_cache
    _limiter = None
    _storage = None
    _http_limit_cache = None


def _window_limit(settings: Settings, max_runs: int) -> RateLimitItem:
    window = max(1, settings.rate_limit_window_seconds)
    return parse(f"{max_runs} per {window} second")


def _global_http_limit(settings: Settings) -> RateLimitItem:
    global _http_limit_cache
    per_min = max(1, int(settings.rate_limit_http_per_minute))
    if _http_limit_cache is not None and _http_limit_cache[0] == per_min:
        return _http_limit_cache[1]
    item = parse(f"{per_min} per minute")
    _http_limit_cache = (per_min, item)
    return item


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
) -> Result[None]:
    """
    Enforce per-workflow and per-client run creation limits.

    client_key should be API key hash or client IP for deployed runs.
    """
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return Result.ok(None)

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
            return Result.fail(
                AppError(
                    code=ErrorCode.RATE_LIMIT,
                    message=f"Rate limit exceeded (redis): max 0 runs per {window}s.",
                )
            )
        return Result.ok(None)

    if not allowed:
        log.warning(
            "rate_limit_workflow_exceeded",
            event_domain="rate_limit",
            workflow_id=workflow_id,
            source=source,
            limit=settings.rate_limit_runs_per_workflow,
        )
        return Result.fail(
            AppError(
                code=ErrorCode.RATE_LIMIT,
                message=(
                    f"Rate limit exceeded (workflow:{workflow_id}): "
                    f"max {settings.rate_limit_runs_per_workflow} runs per {window}s."
                ),
            )
        )

    if not client_key:
        return Result.ok(None)

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
            return Result.fail(
                AppError(
                    code=ErrorCode.RATE_LIMIT,
                    message=f"Rate limit exceeded (redis): max 0 runs per {window}s.",
                )
            )
        return Result.ok(None)

    if not allowed:
        log.warning(
            "rate_limit_client_exceeded",
            event_domain="rate_limit",
            client_key=client_key,
            limit=settings.rate_limit_runs_per_client,
        )
        return Result.fail(
            AppError(
                code=ErrorCode.RATE_LIMIT,
                message=(
                    f"Rate limit exceeded (client): "
                    f"max {settings.rate_limit_runs_per_client} runs per {window}s."
                ),
            )
        )
    return Result.ok(None)


async def check_global_http_rate_limit(client_ip: str) -> bool:
    """Return True when the request is allowed under the global HTTP limit."""
    settings = get_settings()
    limiter = await _get_limiter()
    try:
        return await limiter.hit(_global_http_limit(settings), f"audit:rl:http:{client_ip}")
    except Exception as exc:
        log.warning(
            "rate_limit_redis_unavailable",
            event_domain="rate_limit",
            error_type=type(exc).__name__,
            error_message=repr(exc),
        )
        return _allow_on_redis_error(settings)


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limit for mutating requests (POST/PUT/PATCH/DELETE).

    Browse and poll GETs are excluded so UI refresh / status polling do not
    compete with enqueue for the global budget. Run creation still has
    dedicated per-workflow / per-client limits.
    """

    _MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    async def dispatch(self, request: Request, call_next) -> Response:
        if not get_settings().rate_limit_enabled:
            return await call_next(request)
        if request.method not in self._MUTATING:
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
