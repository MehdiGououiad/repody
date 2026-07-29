"""Cached inference availability checks — avoid ping on every LLM call."""

from __future__ import annotations

import time

from repody.inference.factory import get_ensure_available

_cached_at: float = 0.0
_cached_ok: bool = False
_TTL_SECONDS = 45.0


async def inference_available() -> bool:
    global _cached_at, _cached_ok
    now = time.monotonic()
    if now - _cached_at < _TTL_SECONDS:
        return _cached_ok
    ok = await get_ensure_available()()
    _cached_at = now
    _cached_ok = ok
    return ok


def clear_availability_cache() -> None:
    global _cached_at, _cached_ok
    _cached_at = 0.0
    _cached_ok = False
