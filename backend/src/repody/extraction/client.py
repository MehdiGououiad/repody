"""OpenAI-compatible model servers (llama-server or vLLM), through the official openai SDK."""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from repody.settings import get_settings

_clients: dict[tuple[str, str], AsyncOpenAI] = {}


def _client(base_url: str, api_key: str) -> AsyncOpenAI:
    """One client per server, reused across requests."""
    if (base_url, api_key) not in _clients:
        _clients[base_url, api_key] = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=get_settings().inference_timeout_seconds,
            max_retries=2,
        )
    return _clients[base_url, api_key]


async def chat(
    request: dict[str, Any], *, base_url: str | None = None, api_key: str | None = None
) -> str:
    """Text of the first choice of ``chat.completions.create(**request)``, sent to the NuExtract
    server unless another ``base_url`` is given."""
    settings = get_settings()
    client = _client(base_url or settings.llamacpp_base_url, api_key or settings.llamacpp_api_key)
    response = await client.chat.completions.create(**request)
    return (response.choices[0].message.content or "").strip()


async def model_available() -> bool:
    """Whether the NuExtract server answers and serves the configured model."""
    settings = get_settings()
    client = _client(settings.llamacpp_base_url, settings.llamacpp_api_key)
    try:
        models = await client.with_options(timeout=5, max_retries=0).models.list()
    except Exception:
        return False
    return any(model.id == settings.llamacpp_served_model for model in models.data)


async def close() -> None:
    for client in _clients.values():
        await client.close()
    _clients.clear()
