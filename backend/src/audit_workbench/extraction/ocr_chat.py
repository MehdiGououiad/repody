"""Shared OpenAI-compatible chat helpers for markdown OCR adapters (GLM)."""

from __future__ import annotations

import base64
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from audit_workbench.extraction.schema import empty_fields_from_schema
from audit_workbench.extraction.types import (
    ExtractionResult,
    SchemaFieldSpec,
    truncate_text,
)
from audit_workbench.extraction.render import pages_dropped
from audit_workbench.inference.openai_compat import post_chat_completion

log = structlog.get_logger()


def markdown_from_chat_response(payload: dict[str, Any]) -> str:
    """Extract assistant text from an OpenAI chat/completions response."""
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return ""


def encode_png_image_part(page_png: bytes) -> dict[str, Any]:
    b64 = base64.b64encode(page_png).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{b64}"},
    }


def build_ocr_user_content(
    page_png: bytes,
    *,
    text_prompt: str | None,
) -> list[dict[str, Any]]:
    """Official llama.cpp OCR order: image first, optional text prompt after."""
    content: list[dict[str, Any]] = [encode_png_image_part(page_png)]
    if text_prompt is not None and text_prompt.strip():
        content.append({"type": "text", "text": text_prompt.strip()})
    return content


async def ocr_page_chat(
    *,
    base_url: str,
    model: str,
    page_png: bytes,
    timeout: float,
    text_prompt: str | None,
    max_tokens: int,
    temperature: float,
    top_p: float,
    top_k: int,
    extra: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": build_ocr_user_content(page_png, text_prompt=text_prompt),
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
    }
    if extra:
        payload.update(extra)
    response = await post_chat_completion(base_url, payload, timeout=timeout)
    return markdown_from_chat_response(response)


async def extract_markdown_via_ocr_chat(
    *,
    catalog_id: str,
    runtime: str,
    base_url: str,
    model: str,
    timeout: float,
    pages: list[bytes],
    total_pages: int,
    schema: list[SchemaFieldSpec],
    text_prompt: str | None,
    max_tokens: int,
    temperature: float,
    top_p: float,
    top_k: int,
    empty_error: str,
    log_event: str,
    extra: dict[str, Any] | None = None,
    ocr_one: Callable[..., Awaitable[str]] | None = None,
) -> ExtractionResult:
    """Run per-page OCR chat and join page markdown."""
    if not pages:
        raise RuntimeError(f"{catalog_id} render produced no pages.")

    call = ocr_one or ocr_page_chat
    started = time.perf_counter()
    chunks: list[str] = []
    for page_png in pages:
        text = await call(
            base_url=base_url,
            model=model,
            page_png=page_png,
            timeout=timeout,
            text_prompt=text_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            extra=extra,
        )
        if text.strip():
            chunks.append(text.strip())
    markdown = "\n\n".join(chunks).strip()
    if not markdown:
        raise RuntimeError(empty_error)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    sent = len(pages)
    dropped = pages_dropped(rendered=total_pages, sent=sent)
    log.info(
        log_event,
        catalog_id=catalog_id,
        runtime=runtime,
        pages_sent=sent,
        pages_dropped=dropped,
        markdown_chars=len(markdown),
        elapsed_ms=elapsed_ms,
        base_url=base_url,
        model=model,
    )
    return ExtractionResult(
        fields=empty_fields_from_schema(schema),
        raw_text=None,
        # Keep OCR text verbatim — do not run NuExtract UI markdown_normalize.
        markdown_text=truncate_text(markdown),
        pages_rendered=total_pages,
        pages_sent=sent,
        pages_dropped=dropped,
    )
