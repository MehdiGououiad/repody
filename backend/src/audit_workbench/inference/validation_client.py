"""OpenAI-compatible client for LLM rule validation."""

from __future__ import annotations

import time
from typing import Any

import structlog

from audit_workbench.inference.base import InferenceClient
from audit_workbench.inference.openai_compat import ping_openai_compat, post_chat_completion
from audit_workbench.inference.runtime import llamacpp_base_url
from audit_workbench.inference.validation_model import VALIDATION_MODEL_REQUIRED_MSG
from audit_workbench.settings import Settings

log = structlog.get_logger()


class ValidationInferenceClient(InferenceClient):
    """Text chat against the validation model on the inference endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = llamacpp_base_url(settings)
        self._default_model = (settings.validation_model or "").strip() or None
        self._timeout = settings.validation_timeout_seconds

    @property
    def is_available(self) -> bool:
        return True

    async def chat(self, messages: list[dict[str, Any]], **opts: Any) -> str:
        model = opts.pop("model", None) or self._default_model
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
        data = await post_chat_completion(
            self._base_url,
            payload,
            timeout=self._timeout,
        )
        content = str(data["choices"][0]["message"]["content"])
        log.info(
            "validation_chat_done",
            model=model,
            total_ms=int((time.perf_counter() - started) * 1000),
            output_tokens=(data.get("usage") or {}).get("completion_tokens"),
        )
        return content

    async def ping(self) -> bool:
        return await ping_openai_compat(self._base_url, timeout=5.0)
