from __future__ import annotations

import asyncio
import base64
import io
import json
import time
from typing import TYPE_CHECKING, Any

import structlog

from audit_workbench.extraction.base import ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.field_json import parse_fields_json
from audit_workbench.extraction.template_type_inference import (
    resolve_template_type,
    vlm_max_tokens_for_field_count,
    vlm_max_tokens_for_markdown,
)
from audit_workbench.inference.openai_compat import post_chat_completion
from audit_workbench.inference.runtime import openai_base_url_for_runtime
from audit_workbench.settings import Settings, get_settings

if TYPE_CHECKING:
    from audit_workbench.extraction.model_registry import DocumentModelSpec

log = structlog.get_logger()

type VlmPage = tuple[bytes, str]

_MONEY_HINTS = (
    "amount",
    "total",
    "tax",
    "tva",
    "ttc",
    "price",
    "prix",
    "cost",
    "fee",
    "montant",
    "balance",
)


async def warmup_repody_vlm() -> str:
    """Load Repody VLM weights with a tiny image request on the active runtime.

    Returns: ``ok`` | ``skipped`` | ``failed`` | ``disabled``
    """
    from audit_workbench.extraction.model_registry import parse_document_model

    settings = get_settings()
    if not settings.repody_vlm_warmup_on_start:
        return "disabled"
    if not settings.repody_vlm_enabled:
        return "skipped"
    spec = parse_document_model(None)
    base_url = openai_base_url_for_runtime(spec.runtime, settings)
    from PIL import Image

    image = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(image, format="JPEG", quality=70)
    encoded = base64.b64encode(image.getvalue()).decode("ascii")
    payload = {
        "model": spec.runtime_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                ],
            }
        ],
        "max_tokens": 8,
        "temperature": 0.0,
        "stream": False,
        "chat_template_kwargs": {
            "template": json.dumps({"warmup": "verbatim-string"}),
            "instructions": "Warm up the model. Return null when the field is absent.",
            "enable_thinking": False,
        },
    }
    try:
        started = time.perf_counter()
        await post_chat_completion(
            base_url,
            payload,
            timeout=settings.repody_vlm_timeout_seconds,
        )
        log.info(
            "repody_vlm_warmup_done",
            runtime=spec.runtime,
            model=spec.runtime_model,
            ms=int((time.perf_counter() - started) * 1000),
        )
        return "ok"
    except Exception as exc:
        log.warning("repody_vlm_warmup_failed", runtime=spec.runtime, error=repr(exc))
        return "failed"


def build_vlm_template(schema: list[SchemaFieldSpec]) -> dict[str, str]:
    template: dict[str, str] = {}
    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        template[name] = resolve_template_type(name, field.description, field.template_type)
    return template


def build_vlm_instructions(
    schema: list[SchemaFieldSpec],
    *,
    document_instructions: str = "",
) -> str:
    """NuExtract instructions from per-document notes and field descriptions."""
    lines: list[str] = []
    doc_block = (document_instructions or "").strip()
    if doc_block:
        lines.append(doc_block)
    field_lines: list[str] = []
    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        description = (field.description or "").strip()
        if description:
            field_lines.append(f"- `{name}`: {description}")
    if field_lines:
        lines.append("Field instructions:")
        lines.extend(field_lines)
    return "\n".join(lines)


def _vlm_temperature(*, enable_thinking: bool, markdown: bool = False) -> float:
    """NuExtract docs: 0.2 non-thinking; 0.6 thinking extraction; ~1.0 thinking markdown."""
    if not enable_thinking:
        return 0.2
    return 1.0 if markdown else 0.6


def strip_vlm_thinking(raw: str) -> str:
    """Drop NuExtract reasoning wrapper when thinking mode is enabled."""
    if "</think>" in raw:
        return raw.split("</think>", 1)[1].strip()
    return raw.strip()


def cap_vlm_pages(pages: list[bytes], *, max_pages: int) -> tuple[list[bytes], int]:
    """Limit pages in one Repody VLM request; return (kept_pages, dropped_count)."""
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if len(pages) <= max_pages:
        return pages, 0
    return pages[:max_pages], len(pages) - max_pages


def _vlm_render_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "document_render_max_edge_px": settings.repody_vlm_max_edge_px,
            "document_render_pdf_dpi": settings.repody_vlm_pdf_dpi,
            "ocr_jpeg_quality": settings.repody_vlm_jpeg_quality,
            "ocr_jpeg_optimize": False,
        }
    )


def _image_mime_type(mime_type: str, image_bytes: bytes) -> str:
    mime = (mime_type or "").lower()
    if mime == "image/png" or image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if mime in {"image/webp", "image/x-webp"} or image_bytes.startswith(b"RIFF"):
        return "image/webp"
    if mime in {"image/jpeg", "image/jpg"} or image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/jpeg"


def _vlm_pages(bundle: DocumentBundle, settings: Settings) -> tuple[list[VlmPage], int]:
    mime = (bundle.mime_type or "").lower()
    if mime.startswith("image/") and not bundle.raw_bytes.startswith(b"%PDF"):
        bundle.page_count = 1
        return [(bundle.raw_bytes, _image_mime_type(mime, bundle.raw_bytes))], 1

    if mime == "application/pdf" or bundle.raw_bytes.startswith(b"%PDF"):
        from audit_workbench.extraction.preprocess import render_pdf_pages_png

        pages = render_pdf_pages_png(
            bundle.raw_bytes,
            settings=settings,
            dpi=settings.repody_vlm_pdf_dpi,
            max_edge=settings.repody_vlm_max_edge_px,
        )
        bundle.page_count = len(pages)
        return [(page, "image/png") for page in pages], len(pages)

    pages = bundle.page_jpegs(_vlm_render_settings(settings))
    return [(page, "image/jpeg") for page in pages], len(pages)


def _encode_pages_for_vlm(pages: list[VlmPage]) -> list[dict[str, Any]]:
    return [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64.b64encode(page).decode('ascii')}"
            },
        }
        for page, mime_type in pages
    ]


def _fields_payload(raw: str, schema: list[SchemaFieldSpec]) -> str:
    try:
        payload = json.loads(raw.strip())
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        try:
            payload = json.loads(raw[start : end + 1]) if start >= 0 and end > start else {}
        except json.JSONDecodeError:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}

    rows: list[dict[str, Any]] = []
    for field in schema:
        value = payload.get(field.name)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        hint = f"{field.name} {field.description}".lower()
        if isinstance(value, (int, float)) and any(token in hint for token in _MONEY_HINTS):
            value = f"{float(value):.2f}"
        rows.append(
            {
                "name": field.name,
                "value": "" if value is None else str(value),
                "confidence": 0.9 if value is not None else None,
            }
        )
    return json.dumps({"fields": rows}, ensure_ascii=False)


def _structured_payload(
    *,
    spec: DocumentModelSpec,
    content: list[dict[str, Any]],
    schema: list[SchemaFieldSpec],
    extraction_instructions: str,
    settings: Settings,
) -> dict[str, Any]:
    template = build_vlm_template(schema)
    instructions = build_vlm_instructions(
        schema,
        document_instructions=extraction_instructions,
    )
    field_count = sum(1 for field in schema if field.name.strip())
    enable_thinking = settings.repody_vlm_enable_thinking
    payload: dict[str, Any] = {
        "model": spec.runtime_model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": vlm_max_tokens_for_field_count(
            field_count,
            enable_thinking=enable_thinking,
        ),
        "temperature": _vlm_temperature(enable_thinking=enable_thinking),
        "stream": False,
        "chat_template_kwargs": {
            "template": json.dumps(template, ensure_ascii=False),
            "enable_thinking": enable_thinking,
        },
    }
    if instructions:
        payload["chat_template_kwargs"]["instructions"] = instructions
    return payload


def _markdown_payload(
    *,
    spec: DocumentModelSpec,
    content: list[dict[str, Any]],
    page_count: int,
    settings: Settings,
) -> dict[str, Any]:
    enable_thinking = settings.repody_vlm_enable_thinking
    return {
        "model": spec.runtime_model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": vlm_max_tokens_for_markdown(
            page_count=page_count,
            ceiling=settings.repody_vlm_markdown_max_tokens,
            enable_thinking=enable_thinking,
        ),
        "temperature": _vlm_temperature(enable_thinking=enable_thinking, markdown=True),
        "stream": False,
        "chat_template_kwargs": {
            "mode": "markdown",
            "enable_thinking": enable_thinking,
        },
    }


async def _fetch_repody_vlm_markdown(
    base_url: str,
    payload: dict[str, Any],
    *,
    settings: Settings,
) -> str | None:
    try:
        data = await post_chat_completion(
            base_url,
            payload,
            timeout=settings.repody_vlm_timeout_seconds,
        )
    except Exception as exc:
        log.warning("repody_vlm_markdown_failed", error=repr(exc))
        return None
    raw = strip_vlm_thinking(str(data["choices"][0]["message"]["content"]))
    return raw or None


async def extract_with_repody_vlm(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec | None = None,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
) -> ExtractionResult:
    from audit_workbench.extraction.model_registry import parse_document_model

    settings = get_settings()
    spec = spec or parse_document_model(None)
    base_url = openai_base_url_for_runtime(spec.runtime, settings)
    all_pages, pages_rendered = _vlm_pages(bundle, settings)
    max_pages = min(settings.ocr_max_pages, settings.repody_vlm_max_pages_per_request)
    pages, dropped = cap_vlm_pages(all_pages, max_pages=max_pages)
    if dropped:
        log.warning(
            "repody_vlm_pages_capped",
            rendered=pages_rendered,
            sent=len(pages),
            dropped=dropped,
            max_pages=max_pages,
        )
    content = await asyncio.to_thread(_encode_pages_for_vlm, pages)
    structured_payload = _structured_payload(
        spec=spec,
        content=content,
        schema=schema,
        extraction_instructions=extraction_instructions,
        settings=settings,
    )
    markdown_payload = (
        _markdown_payload(
            spec=spec,
            content=content,
            page_count=len(pages),
            settings=settings,
        )
        if markdown_extraction and settings.repody_vlm_markdown_on_extract
        else None
    )

    started = time.perf_counter()
    if markdown_payload is not None:
        structured_result, markdown_result = await asyncio.gather(
            post_chat_completion(
                base_url,
                structured_payload,
                timeout=settings.repody_vlm_timeout_seconds,
            ),
            _fetch_repody_vlm_markdown(
                base_url,
                markdown_payload,
                settings=settings,
            ),
            return_exceptions=True,
        )
        if isinstance(structured_result, BaseException):
            raise structured_result
        data = structured_result
        markdown_text = None if isinstance(markdown_result, BaseException) else markdown_result
        if isinstance(markdown_result, BaseException):
            log.warning("repody_vlm_markdown_failed", error=repr(markdown_result))
    else:
        data = await post_chat_completion(
            base_url,
            structured_payload,
            timeout=settings.repody_vlm_timeout_seconds,
        )
        markdown_text = None

    raw = strip_vlm_thinking(str(data["choices"][0]["message"]["content"]))
    fields = parse_fields_json(_fields_payload(raw, schema), schema)
    timings = data.get("timings") or {}
    log.info(
        "repody_vlm_done",
        runtime=spec.runtime,
        model=spec.runtime_model,
        pages=len(pages),
        pages_rendered=pages_rendered,
        pages_dropped=dropped,
        max_tokens=structured_payload["max_tokens"],
        markdown=markdown_payload is not None,
        thinking=settings.repody_vlm_enable_thinking,
        markdown_chars=len(markdown_text or ""),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        prompt_ms=int(timings.get("prompt_ms") or 0),
        predicted_ms=int(timings.get("predicted_ms") or 0),
        output_tokens=(data.get("usage") or {}).get("completion_tokens"),
        extracted=sum(1 for field in fields if field.extracted),
    )
    return ExtractionResult(
        fields=fields,
        raw_text=raw,
        ocr_text=markdown_text,
        pages_rendered=pages_rendered,
        pages_sent=len(pages),
        pages_dropped=dropped,
    )
