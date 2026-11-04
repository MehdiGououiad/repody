"""The llama-server, through the official openai SDK (one client per event loop)."""

from __future__ import annotations

import asyncio
from typing import Any

from openai import AsyncOpenAI

from repody.settings import get_settings

# Standard chat.completions arguments; the rest (llama-server's chat_template_kwargs) goes
# through `extra_body`.
_STANDARD_KEYS = frozenset({"model", "messages", "temperature"})

_clients: dict[int, AsyncOpenAI] = {}


def _client() -> AsyncOpenAI:
    loop = id(asyncio.get_running_loop())
    if loop not in _clients:
        settings = get_settings()
        _clients[loop] = AsyncOpenAI(
            base_url=settings.llamacpp_base_url,
            api_key=settings.llamacpp_api_key,
            timeout=settings.inference_timeout_seconds,
            max_retries=2,
        )
    return _clients[loop]


async def chat(payload: dict[str, Any]) -> str:
    """Text of the first choice of a chat completion."""
    standard = {k: v for k, v in payload.items() if k in _STANDARD_KEYS}
    extra = {k: v for k, v in payload.items() if k not in _STANDARD_KEYS}
    response = await _client().chat.completions.create(**standard, extra_body=extra or None)
    return (response.choices[0].message.content or "").strip()


async def model_available() -> bool:
    """Whether the llama-server answers and serves the configured model."""
    served = get_settings().llamacpp_served_model.lower()
    try:
        models = await _client().with_options(timeout=5, max_retries=0).models.list()
    except Exception:
        return False
    return any(m.id.lower().removesuffix(":latest") == served for m in models.data)


async def close() -> None:
    for client in _clients.values():
        await client.close()
    _clients.clear()
