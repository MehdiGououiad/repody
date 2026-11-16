"""OpenAI-compatible model servers (llama-server or vLLM), through the official openai SDK.

Each server takes at most AUDIT_INFERENCE_CONCURRENCY requests from one process at a time (its
parallel slots), so documents and pages can be sent concurrently without queueing on it.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import openai
from openai import AsyncOpenAI

from repody.settings import get_settings

# A model server that is up answers its model list in well under this; one that scales to zero
# (Modal) holds the request while its container starts.
WAKE_PROBE_SECONDS = 2.0

_clients: dict[tuple[str, str], AsyncOpenAI] = {}
_slots: dict[str, asyncio.Semaphore] = {}  # requests in flight, per server


@dataclass(frozen=True, slots=True)
class Reply:
    text: str
    truncated: bool  # the model stopped at its token limit: the answer is incomplete


def _client(base_url: str, api_key: str) -> AsyncOpenAI:
    """One client (connection pool) per server, reused across requests."""
    if (base_url, api_key) not in _clients:
        # No retries: a request that timed out may have kept the GPU busy for the whole timeout,
        # and the document reports its failure instead (the run's other documents go on).
        _clients[base_url, api_key] = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=get_settings().inference_timeout_seconds,
            max_retries=0,
        )
    return _clients[base_url, api_key]


async def chat(request: dict[str, Any]) -> Reply:
    """The first choice of ``chat.completions.create(**request)`` from the NuExtract server."""
    settings = get_settings()
    base_url = settings.llamacpp_base_url
    client = _client(base_url, settings.llamacpp_api_key.get_secret_value())
    slots = _slots.setdefault(base_url, asyncio.Semaphore(get_settings().inference_concurrency))
    async with slots:
        response = await client.chat.completions.create(**request)
    choice = response.choices[0]
    return Reply(
        text=(choice.message.content or "").strip(), truncated=choice.finish_reason == "length"
    )


async def wake(on_asleep: Callable[[], Awaitable[None]]) -> bool:
    """Wait until the NuExtract server is up, calling ``on_asleep`` first if it is starting
    (it scales to zero after idle time); True when it was asleep. Errors are left to the
    extraction requests, which report them on the document."""
    settings = get_settings()
    client = _client(settings.llamacpp_base_url, settings.llamacpp_api_key.get_secret_value())
    try:
        await client.with_options(timeout=WAKE_PROBE_SECONDS, max_retries=0).models.list()
        return False
    except openai.APITimeoutError:
        pass
    except openai.APIError:
        return False
    await on_asleep()
    with contextlib.suppress(openai.APIError):
        await client.with_options(max_retries=0).models.list()  # the inference timeout
    return True


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
