from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from audit_workbench.inference.base import InferenceClient
from audit_workbench.inference.http_pool import get_async_http_client
from audit_workbench.inference.validation_model import VALIDATION_MODEL_REQUIRED_MSG
from audit_workbench.settings import Settings

log = structlog.get_logger()

_RETRYABLE = (httpx.HTTPError, httpx.TimeoutException)


class DockerModelRunnerInferenceClient(InferenceClient):
    def __init__(self, settings: Settings) -> None:
        self._base = settings.docker_model_runner_base_url.rstrip("/")
        self._model = (settings.validation_model or "").strip() or None
        self._timeout = settings.validation_timeout_seconds

    @property
    def is_available(self) -> bool:
        return True

    async def chat(self, messages: list[dict[str, Any]], **opts: Any) -> str:
        model = opts.pop("model", None) or self._model
        if not model:
            raise ValueError(VALIDATION_MODEL_REQUIRED_MSG)
        max_tokens = opts.pop("max_tokens", 128)
        format_json = opts.pop("format_json", False)
        opts.pop("num_ctx", None)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": opts.pop("temperature", 0.0),
            **opts,
        }
        if format_json:
            payload["response_format"] = {"type": "json_object"}
        return await self._post_chat(payload)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    async def _post_chat(self, payload: dict[str, Any]) -> str:
        started = time.perf_counter()
        client = get_async_http_client(self._timeout)
        response = await client.post(
            f"{self._base}/chat/completions",
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        content = str(data["choices"][0]["message"]["content"])
        timings = data.get("timings") or {}
        log.info(
            "docker_model_runner_chat_done",
            model=payload.get("model"),
            total_ms=int((time.perf_counter() - started) * 1000),
            prompt_ms=int(timings.get("prompt_ms") or 0),
            predicted_ms=int(timings.get("predicted_ms") or 0),
            output_tokens=(data.get("usage") or {}).get("completion_tokens"),
        )
        return content

    async def ping(self) -> bool:
        try:
            client = get_async_http_client(5.0)
            response = await client.get(f"{self._base}/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
