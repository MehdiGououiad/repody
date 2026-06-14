from __future__ import annotations

import asyncio

import httpx

# Single long-lived client — per-request timeouts passed at call sites.
_READ_TIMEOUT_S = 600.0
_client: httpx.AsyncClient | None = None
_client_loop_id: int | None = None


def get_async_http_client(timeout: float = 180.0) -> httpx.AsyncClient:
    global _client, _client_loop_id
    _ = timeout  # callers may pass worker/api defaults; use shared read ceiling
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = None

    stale_loop = (
        _client_loop_id is not None
        and loop_id is not None
        and loop_id != _client_loop_id
    )
    if _client is None or _client.is_closed or stale_loop:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(_READ_TIMEOUT_S, connect=15.0),
            limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
        )
        _client_loop_id = loop_id
    return _client


async def close_async_http_client() -> None:
    global _client, _client_loop_id
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
    _client_loop_id = None
