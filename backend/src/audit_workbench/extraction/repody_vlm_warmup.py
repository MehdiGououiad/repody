from __future__ import annotations

import asyncio
import mimetypes
import time
from pathlib import Path

import structlog

from audit_workbench.catalog.registry import parse_document_model
from audit_workbench.extraction.base import SchemaFieldSpec
from audit_workbench.extraction.document_bundle import load_document_bundle
from audit_workbench.extraction.repody_vlm_pages import _encode_pages_for_vlm, _vlm_pages, cap_vlm_pages
from audit_workbench.extraction.nuextract_contract import NUEXTRACT_MAX_PAGES_PER_REQUEST
from audit_workbench.extraction.repody_vlm_payloads import _structured_payload
from audit_workbench.inference.openai_compat import post_chat_completion
from audit_workbench.inference.runtime import llamacpp_base_url
from audit_workbench.settings import Settings, get_settings

log = structlog.get_logger()

_INVOICE_WARMUP_SCHEMA = (
    SchemaFieldSpec(
        name="invoice_number",
        description="Unique identifier, usually near the header.",
    ),
    SchemaFieldSpec(
        name="vendor_name",
        description="Legal name of the vendor issuing the invoice.",
    ),
    SchemaFieldSpec(
        name="subtotal",
        description="Sum of line items before tax.",
        template_type="number",
    ),
    SchemaFieldSpec(
        name="tax",
        description="Total tax amount applied.",
        template_type="number",
    ),
    SchemaFieldSpec(
        name="total_amount",
        description="Final amount due, including taxes and fees.",
        template_type="number",
    ),
    SchemaFieldSpec(
        name="po_number",
        description="Purchase order number referenced on the invoice.",
    ),
)
_WARMUP_PROFILES: tuple[tuple[str, str, tuple[SchemaFieldSpec, ...]], ...] = (
    ("invoice-audit", "Invoice", _INVOICE_WARMUP_SCHEMA),
    (
        "total-only",
        "Facture 1",
        (
            SchemaFieldSpec(
                name="total_amount",
                description="Total TTC",
                template_type="number",
            ),
        ),
    ),
)


def _resolve_warmup_document(settings: Settings) -> Path:
    from audit_workbench.integration.fixtures import repo_root, resolve_facture_pdf

    raw = (settings.repody_vlm_warmup_document or "").strip()
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else repo_root() / path
    return resolve_facture_pdf()


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


async def warmup_repody_vlm() -> str:
    """Prime Repody VLM with a production-shaped NuExtract request.

    Uses the same PDF render path and structured payload as extraction so
    llama-server prompt cache is hot before the first user document.

    Returns: ``ok`` | ``skipped`` | ``failed`` | ``disabled``
    """
    settings = get_settings()
    if not settings.repody_vlm_warmup_on_start:
        return "disabled"
    if not settings.repody_vlm_enabled:
        return "skipped"

    fixture_path = _resolve_warmup_document(settings)
    if not fixture_path.is_file():
        log.warning(
            "repody_vlm_warmup_skipped",
            reason="fixture_missing",
            path=str(fixture_path),
        )
        return "skipped"

    spec = parse_document_model(None)
    base_url = llamacpp_base_url(settings)
    bundle = load_document_bundle(
        fixture_path.read_bytes(),
        _mime_type_for_path(fixture_path),
    )
    all_pages, pages_rendered = _vlm_pages(bundle)
    max_pages = NUEXTRACT_MAX_PAGES_PER_REQUEST
    pages, dropped = cap_vlm_pages(all_pages, max_pages=max_pages)
    content = await asyncio.to_thread(_encode_pages_for_vlm, pages)

    try:
        for profile_name, document_type, schema in _WARMUP_PROFILES:
            payload = _structured_payload(
                spec=spec,
                content=content,
                schema=list(schema),
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
                profile=profile_name,
                runtime=spec.runtime,
                model=spec.runtime_model,
                document=str(fixture_path),
                document_type=document_type,
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
            document=str(fixture_path),
            error=repr(exc),
        )
        return "failed"
