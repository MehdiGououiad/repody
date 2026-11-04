"""The llama-server, through the official openai SDK."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI

from repody.settings import get_settings


@lru_cache
def _client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        base_url=settings.llamacpp_base_url,
        api_key=settings.llamacpp_api_key,
        timeout=settings.inference_timeout_seconds,
        max_retries=2,
    )


async def chat(request: dict[str, Any]) -> str:
    """Text of the first choice of a ``chat.completions.create(**request)`` call."""
    response = await _client().chat.completions.create(**request)
    return (response.choices[0].message.content or "").strip()


async def model_available() -> bool:
    """Whether the llama-server answers and serves the configured model."""
    served = get_settings().llamacpp_served_model
    try:
        models = await _client().with_options(timeout=5, max_retries=0).models.list()
    except Exception:
        return False
    return any(model.id == served for model in models.data)


async def close() -> None:
    if _client.cache_info().currsize:
        await _client().close()
        _client.cache_clear()
