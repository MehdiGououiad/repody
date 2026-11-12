"""OpenAI-compatible model servers (llama-server or vLLM), through the official openai SDK.

Each server takes at most AUDIT_INFERENCE_CONCURRENCY requests from one process at a time (its
parallel slots), so documents and pages can be sent concurrently without queueing on it.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import openai
from openai import AsyncOpenAI

from repody.settings import get_settings

_clients: dict[tuple[str, str], AsyncOpenAI] = {}
_slots: dict[str, asyncio.Semaphore] = {}  # requests in flight, per server


@dataclass(frozen=True, slots=True)
class Reply:
    text: str
    truncated: bool  # the model stopped at its token limit: the answer is incomplete


def _client(base_url: str, api_key: str) -> AsyncOpenAI:
    """One client (connection pool) per server, reused across requests."""
    if (base_url, api_key) not in _clients:
        _clients[base_url, api_key] = AsyncOpenAI(
            base_url=base_url, api_key=api_key, timeout=get_settings().inference_timeout_seconds
        )
    return _clients[base_url, api_key]


async def chat(
    request: dict[str, Any], *, base_url: str | None = None, api_key: str | None = None
) -> Reply:
    """The first choice of ``chat.completions.create(**request)``, sent to the NuExtract
    server unless another ``base_url`` is given."""
    settings = get_settings()
    base_url = base_url or settings.llamacpp_base_url
    client = _client(base_url, api_key or settings.llamacpp_api_key.get_secret_value())
    slots = _slots.setdefault(base_url, asyncio.Semaphore(get_settings().inference_concurrency))
    async with slots:
        response = await client.chat.completions.create(**request)
    choice = response.choices[0]
    return Reply(
        text=(choice.message.content or "").strip(), truncated=choice.finish_reason == "length"
    )


async def model_available() -> bool | None:
    """Whether the NuExtract server answers and serves the configured model; None when it is not
    asked (AUDIT_LLAMACPP_PROBE=false, an endpoint that scales to zero)."""
    settings = get_settings()
    if not settings.llamacpp_probe:
        return None
    client = _client(settings.llamacpp_base_url, settings.llamacpp_api_key.get_secret_value())
    try:
        models = await client.with_options(timeout=5, max_retries=0).models.list()
    except openai.APIError:  # connection, timeout and HTTP errors
        return False
    return any(model.id == settings.llamacpp_served_model for model in models.data)


async def close() -> None:
    for client in _clients.values():
        await client.close()
    _clients.clear()
    _slots.clear()
