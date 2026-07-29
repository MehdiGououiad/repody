"""OpenAI-compatible chat for LLM rule validation."""

from __future__ import annotations

import time
from typing import Any

import structlog

from repody.inference.openai_compat import ping_openai_compat, post_chat_completion
from repody.inference.runtime import llamacpp_base_url
from repody.inference.validation_model import VALIDATION_MODEL_REQUIRED_MSG
from repody.settings import get_settings

log = structlog.get_logger()


async def chat_validation(messages: list[dict[str, Any]], **opts: Any) -> str:
    settings = get_settings()
    base_url = llamacpp_base_url(settings)
    default_model = (settings.validation_model or "").strip() or None
    timeout = settings.validation_timeout_seconds

    model = opts.pop("model", None) or default_model
    if not model:
        raise ValueError(VALIDATION_MODEL_REQUIRED_MSG)
    max_tokens = opts.pop("max_tokens", 128)
    format_json = opts.pop("format_json", False)
    response_format = opts.pop("response_format", None)
    opts.pop("num_ctx", None)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": opts.pop("temperature", 0.0),
        **opts,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    elif format_json:
        payload["response_format"] = {"type": "json_object"}
    started = time.perf_counter()
    data = await post_chat_completion(base_url, payload, timeout=timeout)
    content = str(data["choices"][0]["message"]["content"])
    log.info(
        "validation_chat_done",
        model=model,
        total_ms=int((time.perf_counter() - started) * 1000),
        output_tokens=(data.get("usage") or {}).get("completion_tokens"),
    )
    return content


async def ensure_validation_available() -> bool:
    settings = get_settings()
    return await ping_openai_compat(llamacpp_base_url(settings), timeout=5.0)
