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
from audit_workbench.inference.openai_compat import post_chat_completion
from audit_workbench.inference.runtime import openai_base_url_for_runtime
from audit_workbench.settings import Settings, get_settings

if TYPE_CHECKING:
    from audit_workbench.extraction.model_registry import DocumentModelSpec

log = structlog.get_logger()

_NUMBER_HINTS = (
    "amount",
    "total",
    "tax",
    "tva",
    "ttc",
    "ht",
    "price",
    "prix",
    "cost",
    "fee",
    "quantity",
    "qty",
    "montant",
    "balance",
    "percent",
    "rate",
)
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


def _template_type(field: SchemaFieldSpec) -> str:
    hint = f"{field.name} {field.description}".lower()
    if "date" in hint or "time" in hint:
        return "date-time"
    if any(token in hint for token in _NUMBER_HINTS):
        return "number"
    if "email" in hint:
        return "email"
    if "currency" in hint or "devise" in hint:
        return "currency"
    return "verbatim-string"


def build_vlm_template(schema: list[SchemaFieldSpec]) -> dict[str, str]:
    return {field.name: _template_type(field) for field in schema if field.name.strip()}


def build_vlm_instructions(
    schema: list[SchemaFieldSpec],
    *,
    document_type: str = "",
) -> str:
    """Per-field guidance for Repody VLM structured extraction."""
    doc = (document_type or "document").strip() or "document"
    lines = [
        f"Extract the configured fields from this {doc}.",
        "Use each field name and expected type precisely.",
        "Return null when a field is absent.",
    ]
    field_lines: list[str] = []
    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        description = (field.description or "").strip()
        if description:
            field_lines.append(f"- `{name}`: {description}")
        else:
            field_lines.append(f"- `{name}`")
    if field_lines:
        lines.append("Field guidance:")
        lines.extend(field_lines)
    return "\n".join(lines)


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
            "ocr_jpeg_optimize": False,
        }
    )


def _encode_pages_for_vlm(pages: list[bytes]) -> list[dict[str, Any]]:
    return [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64.b64encode(page).decode('ascii')}"
            },
        }
        for page in pages
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


async def extract_with_repody_vlm(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec | None = None,
) -> ExtractionResult:
    from audit_workbench.extraction.model_registry import parse_document_model

    settings = get_settings()
    spec = spec or parse_document_model(None)
    base_url = openai_base_url_for_runtime(spec.runtime, settings)
    pages = bundle.page_jpegs(_vlm_render_settings(settings))
    max_pages = min(settings.ocr_max_pages, settings.repody_vlm_max_pages_per_request)
    pages, dropped = cap_vlm_pages(pages, max_pages=max_pages)
    if dropped:
        log.warning(
            "repody_vlm_pages_capped",
            rendered=len(pages) + dropped,
            sent=len(pages),
            dropped=dropped,
            max_pages=max_pages,
        )
    content = await asyncio.to_thread(_encode_pages_for_vlm, pages)
    template = build_vlm_template(schema)
    instructions = build_vlm_instructions(schema, document_type=document_type)
    payload = {
        "model": spec.runtime_model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": settings.repody_vlm_max_tokens,
        "temperature": 0.2,
        "stream": False,
        "chat_template_kwargs": {
            "template": json.dumps(template, ensure_ascii=False),
            "instructions": instructions,
            "enable_thinking": False,
        },
    }

    started = time.perf_counter()
    data = await post_chat_completion(
        base_url,
        payload,
        timeout=settings.repody_vlm_timeout_seconds,
    )
    raw = str(data["choices"][0]["message"]["content"])
    fields = parse_fields_json(_fields_payload(raw, schema), schema)
    timings = data.get("timings") or {}
    log.info(
        "repody_vlm_done",
        runtime=spec.runtime,
        model=spec.runtime_model,
        pages=len(pages),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        prompt_ms=int(timings.get("prompt_ms") or 0),
        predicted_ms=int(timings.get("predicted_ms") or 0),
        output_tokens=(data.get("usage") or {}).get("completion_tokens"),
        extracted=sum(1 for field in fields if field.extracted),
    )
    return ExtractionResult(fields=fields, raw_text=raw, ocr_text=raw)
