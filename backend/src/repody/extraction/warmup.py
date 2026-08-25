"""Repody VLM warmup (production-shaped NuExtract request)."""

from __future__ import annotations

import asyncio
import base64
import mimetypes
import time
from pathlib import Path

import structlog

from repody.catalog.registry import parse_document_model
from repody.extraction.nuextract import structured_chat_payload
from repody.extraction.render import (
    encode_pages_as_image_urls,
    pages_dropped,
    prepare_nuextract_pages,
)
from repody.extraction.types import SchemaFieldSpec, load_document_bundle
from repody.inference.openai_compat import post_chat_completion
from repody.inference.runtime import llamacpp_base_url
from repody.settings import Settings, get_settings

log = structlog.get_logger()

_SYNTHETIC_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

_WARMUP_SCHEMA = (
    SchemaFieldSpec(
        name="sample_field",
        description="",
        template_type="verbatim-string",
    ),
)


def _resolve_warmup_document(settings: Settings) -> Path | None:
    raw = (settings.repody_vlm_warmup_document or "").strip()
    if not raw:
        return None
    # Relative paths resolve against the working directory: the package may be
    # installed in site-packages, where its own location says nothing about
    # where the operator's document lives.
    return Path(raw).resolve()


def _mime_type_for_path(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "application/octet-stream"


def _warmup_bundle(settings: Settings):
    fixture_path = _resolve_warmup_document(settings)
    if fixture_path is not None:
        if not fixture_path.is_file():
            return None, str(fixture_path)
        return (
            load_document_bundle(
                fixture_path.read_bytes(),
                _mime_type_for_path(fixture_path),
            ),
            str(fixture_path),
        )
    return (
        load_document_bundle(_SYNTHETIC_PNG, "image/png"),
        "synthetic:1x1.png",
    )


async def warmup_repody_vlm() -> str:
    """Prime Repody VLM with a production-shaped NuExtract request.

    Returns: ``ok`` | ``skipped`` | ``failed`` | ``disabled``
    """
    settings = get_settings()
    if not settings.repody_vlm_warmup_on_start:
        return "disabled"
    if not settings.repody_vlm_enabled:
        return "skipped"

    bundle, document_label = _warmup_bundle(settings)
    if bundle is None:
        log.warning(
            "repody_vlm_warmup_skipped",
            reason="fixture_missing",
            path=document_label,
        )
        return "skipped"

    spec = parse_document_model(None)
    base_url = llamacpp_base_url(settings)
    pages, pages_rendered = prepare_nuextract_pages(
        bundle,
        max_pages=settings.repody_vlm_max_pages_per_request,
    )
    dropped = pages_dropped(rendered=pages_rendered, sent=len(pages))
    content = await asyncio.to_thread(encode_pages_as_image_urls, pages)

    try:
        payload = structured_chat_payload(
            model=spec.runtime_model,
            content=content,
            schema=list(_WARMUP_SCHEMA),
            extraction_instructions="",
        )
        started = time.perf_counter()
        data = await post_chat_completion(
            base_url,
            payload,
            timeout=settings.repody_vlm_timeout_seconds,
        )
        timings = data.get("timings") or {}
        log.info(
            "repody_vlm_warmup_done",
            profile="generic",
            runtime=spec.runtime,
            model=spec.runtime_model,
            document=document_label,
            pages=len(pages),
            pages_rendered=pages_rendered,
            pages_dropped=dropped,
            ms=int((time.perf_counter() - started) * 1000),
            prompt_ms=int(timings.get("prompt_ms") or 0),
            predicted_ms=int(timings.get("predicted_ms") or 0),
        )
        return "ok"
    except Exception as exc:
        log.warning(
            "repody_vlm_warmup_failed",
            runtime=spec.runtime,
            document=document_label,
            error=repr(exc),
        )
        return "failed"
