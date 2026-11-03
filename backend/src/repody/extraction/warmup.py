"""Warm NuExtract with one production-shaped request (extract worker start, llama-serve)."""

from __future__ import annotations

import asyncio
import base64
import time
from pathlib import Path

import filetype
import structlog

from repody.extraction.nuextract import structured_chat_payload
from repody.extraction.render import encode_pages_as_image_urls, prepare_nuextract_pages
from repody.extraction.types import DocumentBundle, SchemaFieldSpec
from repody.inference.openai_compat import post_chat_completion
from repody.inference.runtime import llamacpp_base_url
from repody.settings import get_settings

log = structlog.get_logger()

# 1x1 PNG: enough to load the model and the vision projector.
_SYNTHETIC_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


async def warmup_repody_vlm() -> str:
    """``ok`` | ``skipped`` (warm-up document missing) | ``failed``."""
    settings = get_settings()
    document = settings.repody_vlm_warmup_document
    if document:
        # Relative paths resolve against the working directory, not the installed package.
        path = Path(document).resolve()
        if not path.is_file():
            log.warning("repody_vlm_warmup_skipped", reason="document_missing", path=str(path))
            return "skipped"
        data, label = path.read_bytes(), str(path)
    else:
        data, label = _SYNTHETIC_PNG, "synthetic:1x1.png"

    bundle = DocumentBundle(raw_bytes=data, mime_type=filetype.guess_mime(data) or "")
    try:
        pages, _ = prepare_nuextract_pages(
            bundle, max_pages=settings.repody_vlm_max_pages_per_request
        )
        content = await asyncio.to_thread(encode_pages_as_image_urls, pages)
        started = time.perf_counter()
        await post_chat_completion(
            llamacpp_base_url(settings),
            structured_chat_payload(
                model=settings.llamacpp_served_model,
                content=content,
                schema=[SchemaFieldSpec(name="sample_field")],
                extraction_instructions="",
            ),
            timeout=settings.repody_vlm_timeout_seconds,
        )
    except Exception as exc:
        log.warning("repody_vlm_warmup_failed", document=label, error=repr(exc))
        return "failed"
    log.info(
        "repody_vlm_warmup_done",
        model=settings.llamacpp_served_model,
        document=label,
        pages=len(pages),
        ms=int((time.perf_counter() - started) * 1000),
    )
    return "ok"
