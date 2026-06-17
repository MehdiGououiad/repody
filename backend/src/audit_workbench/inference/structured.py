"""Structured LLM parsing via Docker Model Runner with Pydantic validation."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar, cast

import structlog
from pydantic import BaseModel, ValidationError

from audit_workbench.inference.validation_model import resolve_llm_validation_model
from audit_workbench.settings import get_settings

log = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")

_instructor_client: Any | None = None


def openai_json_schema_format(
    response_model: type[BaseModel],
    *,
    name: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """OpenAI-compatible JSON Schema response_format for constrained decoding."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name or response_model.__name__,
            "strict": strict,
            "schema": response_model.model_json_schema(),
        },
    }


def _get_instructor_client() -> Any:
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


async def _request_structured_raw(
    *,
    messages: list[dict[str, str]],
    response_model: type[T],
    model: str,
    max_tokens: int,
    temperature: float,
    use_json_schema: bool,
) -> str:
    from audit_workbench.inference.factory import get_inference_client

    client = get_inference_client()
    chat_opts: dict[str, Any] = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "model": model,
    }
    if use_json_schema:
        chat_opts["response_format"] = openai_json_schema_format(response_model)
    else:
        chat_opts["format_json"] = True
    return await client.chat(messages, **chat_opts)


async def chat_structured(
    *,
    messages: list[dict[str, str]],
    response_model: type[T],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.0,
    use_json_schema: bool = True,
) -> T:
    """
    Request structured JSON from Docker Model Runner.

    Uses JSON-schema constrained decoding when supported, then Pydantic validation.
    Falls back to json_object mode and instructor when parsing fails.
    """
    settings = get_settings()
    model, model_error = resolve_llm_validation_model(model, settings=settings)
    if model_error:
        raise ValueError(model_error)
    if model is None:
        raise ValueError("AUDIT_VALIDATION_MODEL is required for structured LLM calls.")
    chosen_model = model
    token_limit = max_tokens if max_tokens is not None else settings.validation_max_tokens

    raw = await _request_structured_raw(
        messages=messages,
        response_model=response_model,
        model=chosen_model,
        max_tokens=token_limit,
        temperature=temperature,
        use_json_schema=use_json_schema,
    )
    try:
        return parse_structured_response(response_model, raw)
    except (ValidationError, ValueError) as native_exc:
        if use_json_schema:
            log.warning("json_schema_parse_failed_retrying_json_object", error=repr(native_exc))
            raw = await _request_structured_raw(
                messages=messages,
                response_model=response_model,
                model=chosen_model,
                max_tokens=token_limit,
                temperature=temperature,
                use_json_schema=False,
            )
            try:
                return parse_structured_response(response_model, raw)
            except (ValidationError, ValueError):
                pass
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
    return cast(
        T,
        await structured.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            response_model=response_model,
            max_tokens=max_tokens,
            temperature=temperature,
        ),
    )
