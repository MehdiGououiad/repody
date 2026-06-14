"""Structured LLM parsing via Docker Model Runner with Pydantic validation."""

from __future__ import annotations

import json
import re
from typing import TypeVar

import structlog
from pydantic import BaseModel, ValidationError

from audit_workbench.inference.validation_model import resolve_llm_validation_model
from audit_workbench.settings import get_settings

log = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")

_instructor_client: object | None = None


def _get_instructor_client():
    global _instructor_client
    if _instructor_client is None:
        import instructor
        from openai import AsyncOpenAI

        settings = get_settings()
        oai = AsyncOpenAI(
            base_url=settings.docker_model_runner_base_url,
            api_key="docker-model-runner",
            timeout=60.0,
        )
        _instructor_client = instructor.from_openai(oai, mode=instructor.Mode.JSON)
    return _instructor_client


def extract_json_object(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty LLM response.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(text)
        if not match:
            raise ValueError("LLM response was not valid JSON.") from None
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM JSON payload must be an object.")
    return data


def parse_structured_response(model: type[T], raw: str) -> T:
    """Validate LLM JSON with Pydantic (always available)."""
    return model.model_validate(extract_json_object(raw))


def instructor_available() -> bool:
    try:
        import instructor  # noqa: F401
        import openai  # noqa: F401

        return True
    except ImportError:
        return False


async def chat_structured(
    *,
    messages: list[dict[str, str]],
    response_model: type[T],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.0,
) -> T:
    """
    Request structured JSON from Docker Model Runner.

    Uses the native OpenAI-compatible JSON chat API first. Falls back to
    instructor only when parsing fails and structured LLM is enabled.
    """
    settings = get_settings()
    model, model_error = resolve_llm_validation_model(model, settings=settings)
    if model_error:
        raise ValueError(model_error)
    chosen_model = model
    token_limit = max_tokens if max_tokens is not None else settings.validation_max_tokens

    from audit_workbench.inference.factory import get_inference_client

    client = get_inference_client()
    raw = await client.chat(
        messages,
        max_tokens=token_limit,
        temperature=temperature,
        model=chosen_model,
        format_json=True,
    )
    try:
        return parse_structured_response(response_model, raw)
    except (ValidationError, ValueError) as native_exc:
        if settings.structured_llm_enabled and instructor_available():
            try:
                return await _chat_with_instructor(
                    messages=messages,
                    response_model=response_model,
                    model=chosen_model,
                    max_tokens=token_limit,
                    temperature=temperature,
                )
            except Exception as exc:
                log.warning("instructor_structured_failed", error=repr(exc))
        raise ValueError(f"Structured LLM parse failed: {native_exc}") from native_exc


async def _chat_with_instructor(
    *,
    messages: list[dict[str, str]],
    response_model: type[T],
    model: str,
    max_tokens: int,
    temperature: float,
) -> T:
    structured = _get_instructor_client()
    return await structured.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        response_model=response_model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
