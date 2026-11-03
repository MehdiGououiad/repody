"""Redis-backed rate limiting with the `limits` library (moving window)."""

from __future__ import annotations

import structlog
from limits import parse
from limits.aio.storage import RedisStorage
from limits.aio.strategies import MovingWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from repody.runtime.contracts.result import AppError, ErrorCode
from repody.settings import get_settings

log = structlog.get_logger(__name__)

_limiter: MovingWindowRateLimiter | None = None


def clear_rate_limiter_cache() -> None:
    """Reset the cached limiter (tests)."""
    global _limiter
    _limiter = None


def _get_limiter() -> MovingWindowRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = MovingWindowRateLimiter(RedisStorage(get_settings().redis_url))
    return _limiter


async def _allowed(limit: str, key: str) -> bool:
    """Record one hit; when Redis is down, allow unless AUDIT_RATE_LIMIT_FAIL_CLOSED."""
    try:
        return await _get_limiter().hit(parse(limit), key)
    except Exception as exc:
        log.warning("rate_limit_redis_unavailable", event_domain="rate_limit", error=repr(exc))
        return not get_settings().rate_limit_fail_closed


async def check_run_rate_limits(
    *,
    workflow_id: str,
    source: str,
    client_key: str | None = None,
) -> None:
    """Per-workflow and per-client run creation limits (client_key: API key hash or IP)."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    window = max(1, settings.rate_limit_window_seconds)
    checks = [
        (
            f"workflow:{workflow_id}",
            settings.rate_limit_runs_per_workflow,
            f"wf:{workflow_id}:{source}",
        )
    ]
    if client_key:
        checks.append(("client", settings.rate_limit_runs_per_client, f"client:{client_key}"))
    for scope, max_runs, key in checks:
        if not await _allowed(f"{max_runs} per {window} second", f"audit:rl:{key}"):
            log.warning("rate_limit_exceeded", event_domain="rate_limit", scope=scope)
            raise AppError(
                code=ErrorCode.RATE_LIMIT,
                message=f"Rate limit exceeded ({scope}): max {max_runs} runs per {window}s.",
            )


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP limit for mutating requests (POST/PUT/PATCH/DELETE).

    Browse and poll GETs are excluded so UI refresh and status polling do not compete
    with enqueue; run creation also has its own per-workflow / per-client limits.
    """

    _MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if not settings.rate_limit_enabled or request.method not in self._MUTATING:
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        limit = f"{max(1, settings.rate_limit_http_per_minute)} per minute"
        if not await _allowed(limit, f"audit:rl:http:{client_ip}"):
            return JSONResponse(
                status_code=429, content={"detail": "Rate limit exceeded. Try again later."}
            )
        return await call_next(request)
