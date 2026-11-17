"""The model server (vLLM on Modal, or a local llama-server), through the official openai SDK.

It takes at most AUDIT_INFERENCE_CONCURRENCY requests from one process at a time (its parallel
slots), so documents and pages can be sent concurrently without queueing on it.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import cache
from typing import Any

import openai
from openai import AsyncOpenAI

from repody.settings import get_settings

# A model server that is up answers its model list in well under this; one that scales to zero
# (Modal) holds the request while its container starts.
WAKE_PROBE_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class Reply:
    text: str
    truncated: bool  # the model stopped at its token limit: the answer is incomplete


@cache
def _client() -> AsyncOpenAI:
    """One client (connection pool), reused across requests."""
    settings = get_settings()
    # No retries: a request that timed out may have kept the GPU busy for the whole timeout, and
    # the document reports its failure instead (the run's other documents go on).
    return AsyncOpenAI(
        base_url=settings.inference_base_url,
        api_key=settings.inference_api_key.get_secret_value(),
        timeout=settings.inference_timeout_seconds,
        max_retries=0,
    )


@cache
def _slots() -> asyncio.Semaphore:
    """The requests this process has in flight to the server."""
    return asyncio.Semaphore(get_settings().inference_concurrency)


async def chat(request: dict[str, Any]) -> Reply:
    """The first choice of ``chat.completions.create(**request)`` from the NuExtract server."""
    async with _slots():
        response = await _client().chat.completions.create(**request)
    choice = response.choices[0]
    return Reply(
        text=(choice.message.content or "").strip(), truncated=choice.finish_reason == "length"
    )


async def wake(on_asleep: Callable[[], Awaitable[None]]) -> bool:
    """Wait until the NuExtract server is up, calling ``on_asleep`` first if it is starting
    (it scales to zero after idle time); True when it was asleep. Errors are left to the
    extraction requests, which report them on the document."""
    client = _client()
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
    asked (AUDIT_INFERENCE_PROBE=false, an endpoint that scales to zero)."""
    settings = get_settings()
    if not settings.inference_probe:
        return None
    try:
        models = await _client().with_options(timeout=5, max_retries=0).models.list()
    except openai.APIError:  # connection, timeout and HTTP errors
        return False
    return any(model.id == settings.inference_model for model in models.data)


async def close() -> None:
    """Close the connection pool; the next request opens a new one (with current settings)."""
    if _client.cache_info().currsize:
        await _client().close()
    _client.cache_clear()
    _slots.cache_clear()
