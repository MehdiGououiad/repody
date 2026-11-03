"""Page images for NuExtract: PDF -> PNG @ 170 DPI (official); images pass through."""

from __future__ import annotations

import base64
from typing import Any

import filetype
import pymupdf

from repody.extraction.nuextract import NUEXTRACT_PDF_DPI
from repody.extraction.types import DocumentBundle

PageBytes = tuple[bytes, str]  # (bytes, mime_type)


def prepare_nuextract_pages(
    bundle: DocumentBundle, *, max_pages: int | None = None
) -> tuple[list[PageBytes], int]:
    """``(pages, document_page_count)``; ``max_pages=None`` sends every page (official)."""
    # Trust the bytes over the declared type (browsers mislabel files).
    mime = filetype.guess_mime(bundle.raw_bytes) or (bundle.mime_type or "").lower()
    if mime == "application/pdf":
        with pymupdf.open(stream=bundle.raw_bytes, filetype="pdf") as doc:
            total = len(doc)
            if total == 0:
                raise ValueError("PDF has no pages")
            count = min(total, max_pages) if max_pages else total
            pages = [
                (doc[i].get_pixmap(dpi=NUEXTRACT_PDF_DPI, alpha=False).tobytes("png"), "image/png")
                for i in range(count)
            ]
        return pages, total
    if mime.startswith("image/"):
        return [(bundle.raw_bytes, mime)], 1
    raise ValueError(
        f"Unsupported document type for NuExtract: {bundle.mime_type!r}. "
        "Upload a PDF or an image (PNG, JPEG, WebP)."
    )


def encode_pages_as_image_urls(pages: list[PageBytes]) -> list[dict[str, Any]]:
    """OpenAI-style ``image_url`` content parts (data URLs)."""
    return [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"},
        }
        for data, mime in pages
    ]
