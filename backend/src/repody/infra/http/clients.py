"""Shared ``httpx.AsyncClient`` pool — reuse connections across requests.

Official HTTPX guidance: create clients once, share them, and ``aclose()`` on
shutdown. Per-request ``async with AsyncClient()`` throws away the connection
pool on every call.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

# (base_url, frozen headers, loop id) → client. Timeout is passed per request.
_client_cache: dict[tuple[str, tuple[tuple[str, str], ...], int | None], httpx.AsyncClient] = {}


def _loop_id() -> int | None:
    try:
        return id(asyncio.get_running_loop())
    except RuntimeError:
        return None


def _headers_key(headers: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
    if not headers:
        return ()
    return tuple(sorted((str(k), str(v)) for k, v in headers.items()))


def get_http_client(
    *,
    base_url: str = "",
    headers: Mapping[str, str] | None = None,
) -> httpx.AsyncClient:
    """Return a cached async client for this event loop / base URL / headers.

    Pass ``timeout=…`` on each request (``client.get(url, timeout=10)``) so one
    pooled client can serve both short auth probes and long OCR calls.
    """
    normalized_base = base_url.rstrip("/") if base_url else ""
    header_key = _headers_key(headers)
    cache_key = (normalized_base, header_key, _loop_id())
    cached = _client_cache.get(cache_key)
    if cached is not None:
        return cached

    # High default; callers override per request. Avoids closing the pool early.
    kwargs: dict[str, Any] = {"timeout": httpx.Timeout(600.0)}
    if normalized_base:
        kwargs["base_url"] = normalized_base
    if headers:
        kwargs["headers"] = dict(headers)

    client = httpx.AsyncClient(**kwargs)
    _client_cache[cache_key] = client
    return client


async def close_http_clients() -> None:
    """Close every cached client (API lifespan / worker shutdown / tests)."""
    clients = list(_client_cache.values())
    _client_cache.clear()
    for client in clients:
        await client.aclose()
