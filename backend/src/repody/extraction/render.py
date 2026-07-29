"""Page/image/PDF preparation for document-model adapters.

NuExtract: PDF → PNG @ 170 DPI (official). Images pass through as native bytes.
GLM-OCR: layout SDK loads PDFs itself at pdf_dpi=200.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Literal

from repody.extraction.branding import (
    GLM_OCR_CATALOG_ID,
    REPODY_VLM_CATALOG_ID,
    REPODY_VLM_CLOUD_CATALOG_ID,
)
from repody.extraction.nuextract import NUEXTRACT_PDF_DPI
from repody.extraction.types import DocumentBundle

PageBytes = tuple[bytes, str]  # (bytes, mime_type)

# Official glmocr/config.yaml page_loader.pdf_dpi
GLM_OCR_PDF_DPI = 200


def pages_to_process(doc_page_count: int, max_pages: int | None) -> int:
    """Clamp page count; ``None`` = all pages (official NuExtract)."""
    if doc_page_count <= 0:
        return 0
    if max_pages is None or max_pages < 1:
        return doc_page_count
    return min(doc_page_count, max_pages)


def render_nuextract_pdf_pages(
    document_bytes: bytes,
    *,
    max_pages: int | None = None,
) -> tuple[list[bytes], int]:
    """Official NuExtract PDF input: lossless PNG @ 170 DPI.

    Returns ``(png_pages, total_pdf_page_count)``.
    """
    import fitz

    doc = fitz.open(stream=document_bytes, filetype="pdf")
    try:
        total = len(doc)
        if total <= 0:
            raise ValueError("PDF has no pages")
        page_count = pages_to_process(total, max_pages)
        pages: list[bytes] = []
        for i in range(page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=NUEXTRACT_PDF_DPI, alpha=False)
            pages.append(pix.tobytes("png"))
        return pages, total
    finally:
        doc.close()


@dataclass(frozen=True)
class ModelRenderPolicy:
    """How the platform prepares bytes before calling a model adapter."""

    model_id: str
    doc_ref: str
    image_input: Literal["native_bytes", "pil_rgb"]
    pdf_dpi: int
    pdf_format: Literal["png"]


REPODY_VLM_RENDER = ModelRenderPolicy(
    model_id=REPODY_VLM_CATALOG_ID,
    doc_ref="numind/NuExtract3 (dpi=170 PNG)",
    image_input="native_bytes",
    pdf_dpi=NUEXTRACT_PDF_DPI,
    pdf_format="png",
)

REPODY_VLM_CLOUD_RENDER = ModelRenderPolicy(
    model_id=REPODY_VLM_CLOUD_CATALOG_ID,
    doc_ref="nuextract.ai structured-extraction (upload original PDF/image)",
    image_input="native_bytes",
    pdf_dpi=NUEXTRACT_PDF_DPI,
    pdf_format="png",
)

GLM_OCR_RENDER = ModelRenderPolicy(
    model_id=GLM_OCR_CATALOG_ID,
    doc_ref=(
        "GLM-OCR official SDK (PP-DocLayoutV3 + region OCR; pdf_dpi=200; "
        "Text/Table/Formula Recognition)"
    ),
    image_input="pil_rgb",
    pdf_dpi=GLM_OCR_PDF_DPI,
    pdf_format="png",
)

RENDER_POLICIES: dict[str, ModelRenderPolicy] = {
    REPODY_VLM_RENDER.model_id: REPODY_VLM_RENDER,
    REPODY_VLM_CLOUD_RENDER.model_id: REPODY_VLM_CLOUD_RENDER,
    GLM_OCR_RENDER.model_id: GLM_OCR_RENDER,
}


def _is_pdf(mime_type: str, raw_bytes: bytes) -> bool:
    mime = (mime_type or "").lower()
    return mime == "application/pdf" or raw_bytes.startswith(b"%PDF")


def _is_image(mime_type: str, raw_bytes: bytes) -> bool:
    if _is_pdf(mime_type, raw_bytes):
        return False
    return (mime_type or "").lower().startswith("image/")


def _image_mime(mime_type: str, image_bytes: bytes) -> str:
    mime = (mime_type or "").lower()
    if mime == "image/png" or image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if mime in {"image/webp", "image/x-webp"} or (
        len(image_bytes) >= 12
        and image_bytes[:4] == b"RIFF"
        and image_bytes[8:12] == b"WEBP"
    ):
        return "image/webp"
    if mime in {"image/jpeg", "image/jpg"} or image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/jpeg"


def prepare_nuextract_pages(
    bundle: DocumentBundle,
    *,
    max_pages: int | None = None,
) -> tuple[list[PageBytes], int]:
    """Pages for NuExtract vision: native image, or PDF → PNG @ 170 DPI.

    Returns ``(pages, document_page_count)``.
    """
    if _is_image(bundle.mime_type, bundle.raw_bytes):
        bundle.page_count = 1
        mime = _image_mime(bundle.mime_type, bundle.raw_bytes)
        return [(bundle.raw_bytes, mime)], 1

    if _is_pdf(bundle.mime_type, bundle.raw_bytes):
        pages, total = render_nuextract_pdf_pages(
            bundle.raw_bytes, max_pages=max_pages
        )
        bundle.page_count = total
        return [(page, "image/png") for page in pages], total

    raise ValueError(
        f"Unsupported document type for NuExtract vision: {bundle.mime_type!r}. "
        "Upload a PDF or image (PNG, JPEG, WebP)."
    )


def cap_pages(
    pages: list[PageBytes], *, max_pages: int | None
) -> tuple[list[PageBytes], int]:
    """Limit pages in one request; return ``(kept, dropped_count)``."""
    if max_pages is None:
        return pages, 0
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if len(pages) <= max_pages:
        return pages, 0
    return pages[:max_pages], len(pages) - max_pages


def pages_dropped(*, rendered: int, sent: int) -> int:
    return max(0, int(rendered) - int(sent))


def encode_pages_as_image_urls(pages: list[PageBytes]) -> list[dict[str, Any]]:
    """OpenAI-style ``image_url`` content parts (data URLs)."""
    return [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
            },
        }
        for data, mime in pages
    ]
