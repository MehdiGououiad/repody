from __future__ import annotations

import asyncio
from typing import Any

from openai import AsyncOpenAI

from repody.inference.runtime import openai_api_key_for_base_url

_STANDARD_CHAT_KEYS = frozenset(
    {
        "model",
        "messages",
        "max_tokens",
        "temperature",
        "top_p",
        "stream",
        "response_format",
    }
)

# One SDK client (one connection pool) per endpoint and event loop; timeout and retries are
# set per call with `with_options` (openai-python README). Workers run one loop; tests run many.
_clients: dict[tuple[str, str, int], AsyncOpenAI] = {}

# SDK retries (backoff on 408/429/5xx and connection errors) for real work; probes fail fast.
INFERENCE_MAX_RETRIES = 2


def normalize_openai_model_name(name: str) -> str:
    return name.strip().lower().removesuffix(":latest")


def _client(
    base_url: str, *, timeout: float, api_key: str | None = None, max_retries: int = 0
) -> AsyncOpenAI:
    key = (base_url.rstrip("/"), api_key or openai_api_key_for_base_url(base_url))
    loop_key = (*key, id(asyncio.get_running_loop()))
    client = _clients.get(loop_key)
    if client is None:
        client = _clients[loop_key] = AsyncOpenAI(base_url=key[0], api_key=key[1])
    return client.with_options(timeout=timeout, max_retries=max_retries)


async def close_openai_clients() -> None:
    for client in _clients.values():
        await client.close()
    _clients.clear()


async def list_openai_models(
    base_url: str,
    *,
    timeout: float = 2.0,
    api_key: str | None = None,
) -> set[str]:
    try:
        client = _client(base_url, timeout=timeout, api_key=api_key)
        page = await client.models.list()
        return {normalize_openai_model_name(model.id) for model in page.data if model.id}
    except Exception:
        return set()


async def post_chat_completion(
    base_url: str,
    payload: dict[str, Any],
    *,
    timeout: float,
    api_key: str | None = None,
    max_retries: int = INFERENCE_MAX_RETRIES,
) -> dict[str, Any]:
    client = _client(base_url, timeout=timeout, api_key=api_key, max_retries=max_retries)
    standard, extra = split_chat_payload(payload)
    response = await client.chat.completions.create(**standard, extra_body=extra or None)
    return response.model_dump()


def message_content(completion: dict[str, Any]) -> str:
    """Text of the first choice in a ``chat.completions`` response dict."""
    return str(completion["choices"][0]["message"]["content"])


def split_chat_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split OpenAI SDK params from runtime-specific extension params."""
    standard = {k: payload[k] for k in _STANDARD_CHAT_KEYS if k in payload}
    extra = {k: v for k, v in payload.items() if k not in _STANDARD_CHAT_KEYS}
    return standard, extra


def model_is_available(expected: str, installed: set[str]) -> bool:
    target = normalize_openai_model_name(expected)
    if not target:
        return False
    return target in installed
