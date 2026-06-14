"""Cached inference availability checks — avoid /api/tags on every LLM call."""

from __future__ import annotations

import time

from audit_workbench.inference.base import InferenceClient

_cached_at: float = 0.0
_cached_ok: bool = False
_TTL_SECONDS = 45.0


async def inference_available(client: InferenceClient) -> bool:
    global _cached_at, _cached_ok
    now = time.monotonic()
    if now - _cached_at < _TTL_SECONDS:
        return _cached_ok
    ok = await client.ensure_available()
    _cached_at = now
    _cached_ok = ok
    return ok


def invalidate_inference_availability() -> None:
    global _cached_at
    _cached_at = 0.0
