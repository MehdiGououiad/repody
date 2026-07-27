"""Stub inference chat (LLM validation disabled / stub mode)."""

from __future__ import annotations

from typing import Any


async def chat_stub(messages: list[dict[str, Any]], **opts: Any) -> str:
    _ = messages, opts
    return '{"passed": true, "detail": "Inference disabled (stub mode)."}'


async def ensure_stub_available() -> bool:
    return False
