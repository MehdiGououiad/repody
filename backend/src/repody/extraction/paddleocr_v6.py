"""PP-OCRv6 markdown adapter — official PaddleX Basic Serving client.

Serve (host):
  paddlex --install serving
  paddlex --serve --pipeline deploy/paddleocr-v6/OCR.yaml --host 0.0.0.0 --port 8868

Client (official OCR pipeline serving contract):
  POST /ocr  JSON { "file": "<base64>", "fileType": 0|1, "visualize": false,
                    "useDocOrientationClassify": true,
                    "useDocUnwarping": true,
                    "useTextlineOrientation": true }

Docs:
  https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html
  https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html
"""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx
import structlog

from repody.catalog.adapters import register_document_model_adapter
from repody.catalog.registry import DocumentModelSpec
from repody.extraction.branding import PADDLEOCR_V6_CATALOG_ID
from repody.extraction.schema import empty_fields_from_schema
from repody.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
    truncate_text,
)
from repody.settings import get_settings

log = structlog.get_logger()

# Official fileType: 0 = PDF, 1 = image (incl. TIFF).
FILE_TYPE_PDF = 0
FILE_TYPE_IMAGE = 1


def file_type_for_mime(mime_type: str | None) -> int:
    mime = (mime_type or "").split(";", 1)[0].strip().lower()
    if mime == "application/pdf":
        return FILE_TYPE_PDF
    return FILE_TYPE_IMAGE


def paddle_error_message(body: dict[str, Any], *, label: str) -> str | None:
    """Return an error string when official serving errorCode is non-zero."""
    code = body.get("errorCode")
    if code is None:
        return None
    try:
        if int(code) == 0:
            return None
    except (TypeError, ValueError):
        return f"{label} invalid errorCode: {code!r}"
    return f"{label} error {code}: {body.get('errorMsg') or body}"


def _texts_from_pruned(pruned: dict[str, Any]) -> list[str]:
    """Official prunedResult.rec_texts (snake_case inside prunedResult)."""
    raw = pruned.get("rec_texts")
    if not isinstance(raw, list):
        return []
    return [t if isinstance(t, str) else str(t) for t in raw]


def markdown_from_ocr_result(payload: dict[str, Any]) -> str:
    """Join official ``result.ocrResults[].prunedResult.rec_texts`` lines.

    Pages separated by blank lines; lines joined with ``\\n`` (including empty
    strings as returned by serving).
    """
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return ""
    pages = result.get("ocrResults")
    if not isinstance(pages, list):
        return ""
    chunks: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        pruned = page.get("prunedResult")
        if not isinstance(pruned, dict):
            continue
        lines = _texts_from_pruned(pruned)
        if lines:
            chunks.append("\n".join(lines))
    return "\n\n".join(chunks).strip()


def build_ocr_request_payload(bundle: DocumentBundle) -> dict[str, Any]:
    """Official Basic Serving request body for ``POST /ocr``.

    Same fields as the multi-language examples on the OCR pipeline page:
    ``file`` (Base64) + ``fileType`` (0=PDF, 1=image). ``visualize: false``
    avoids returning large Base64 images (also settable in pipeline Serving).
    The three document-preparation flags are the documented per-request
    overrides. They default to the official pipeline defaults and can be
    disabled for clean, already-oriented documents.
    """
    settings = get_settings()
    return {
        "file": base64.b64encode(bundle.raw_bytes).decode("ascii"),
        "fileType": file_type_for_mime(bundle.mime_type),
        "visualize": False,
        "useDocOrientationClassify": bool(settings.paddleocr_v6_use_doc_orientation_classify),
        "useDocUnwarping": bool(settings.paddleocr_v6_use_doc_unwarping),
        "useTextlineOrientation": bool(settings.paddleocr_v6_use_textline_orientation),
    }


async def fetch_paddleocr_markdown(bundle: DocumentBundle) -> tuple[str, int]:
    """Official ``POST /ocr`` → ``(markdown, page_count)``."""
    settings = get_settings()
    base = (settings.paddleocr_v6_base_url or "").rstrip("/")
    if not base:
        raise RuntimeError(
            "PP-OCRv6 base URL is empty. Set AUDIT_PADDLEOCR_V6_BASE_URL "
            "(example: http://127.0.0.1:8868 after `pnpm paddleocr:v6:serve`)."
        )

    payload = build_ocr_request_payload(bundle)
    url = f"{base}/ocr"
    timeout = float(settings.paddleocr_v6_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
    if response.status_code != 200:
        raise RuntimeError(
            f"PP-OCRv6 /ocr failed HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )
    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("PP-OCRv6 /ocr returned a non-object JSON body.")
    err = paddle_error_message(body, label="PP-OCRv6")
    if err:
        raise RuntimeError(err)
    markdown = markdown_from_ocr_result(body)
    if not markdown.strip():
        raise RuntimeError(
            "PP-OCRv6 returned empty text. Check Basic Serving "
            "(`pnpm paddleocr:v6:serve` / paddlex --serve --pipeline OCR) "
            "and that the document is a supported PDF/image."
        )
    page_count = len((body.get("result") or {}).get("ocrResults") or [])
    return markdown, page_count


async def extract_with_paddleocr_v6(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec | None = None,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    """Markdown-only extraction via official ``POST /ocr`` Basic Serving."""
    _ = document_type
    _ = extraction_instructions
    _ = extraction_icl_examples
    _ = markdown_extraction
    started = time.perf_counter()
    markdown, page_count = await fetch_paddleocr_markdown(bundle)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    base = (get_settings().paddleocr_v6_base_url or "").rstrip("/")
    log.info(
        "paddleocr_v6_done",
        catalog_id=(spec.id if spec else PADDLEOCR_V6_CATALOG_ID),
        runtime="paddleocr_v6",
        pages=page_count or 1,
        markdown_chars=len(markdown),
        elapsed_ms=elapsed_ms,
        base_url=base,
    )
    return ExtractionResult(
        fields=empty_fields_from_schema(schema),
        markdown_text=truncate_text(markdown),
        pages_rendered=page_count,
        pages_sent=page_count,
        pages_dropped=0,
    )


register_document_model_adapter(PADDLEOCR_V6_CATALOG_ID, extract_with_paddleocr_v6)
