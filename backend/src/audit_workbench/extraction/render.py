"""Page/image/PDF preparation for Repody VLM."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Any, Literal

from audit_workbench.extraction.branding import GLM_OCR_CATALOG_ID
from audit_workbench.extraction.nuextract import (
    NUEXTRACT_MAX_PAGES_PER_REQUEST,
    NUEXTRACT_PDF_DPI,
)
from audit_workbench.extraction.types import DocumentBundle

type VlmPage = tuple[bytes, str]

# GLM-OCR — align with zai-org/GLM-OCR SDK page_loader defaults:
#   https://github.com/zai-org/GLM-OCR/blob/main/glmocr/config.yaml
#   https://huggingface.co/zai-org/GLM-OCR
# No platform longest-edge downscale — model smart-resizes via min/max_pixels.
GLM_OCR_PDF_DPI = 200  # official page_loader.pdf_dpi
GLM_OCR_MAX_EDGE_PX: int | None = None  # no platform downscale; model smart-resizes
GLM_OCR_TEMPERATURE = 0.0  # greedy (vLLM recipe + SDK)
GLM_OCR_TOP_P = 0.00001
GLM_OCR_TOP_K = 1
GLM_OCR_REPEAT_PENALTY = 1.1
GLM_OCR_MAX_TOKENS = 8192
GLM_OCR_MAX_PAGES_PER_DOCUMENT = 32
GLM_OCR_TEXT_PROMPT = "Text Recognition:"


def pages_to_process(doc_page_count: int, max_pages: int) -> int:
    """Clamp document page count to the NuExtract per-request limit."""
    if doc_page_count <= 0:
        return 0
    return min(doc_page_count, max(1, max_pages))

def render_nuextract_pdf_pages(document_bytes: bytes) -> tuple[list[bytes], int]:
    """Official NuExtract PDF input: lossless PNG @ 170 DPI.

    Returns ``(png_pages_capped_to_max, total_pdf_page_count)`` so callers can
    report pages dropped when the document exceeds the per-request limit.
    """
    import fitz

    doc = fitz.open(stream=document_bytes, filetype="pdf")
    try:
        total = len(doc)
        if total <= 0:
            raise ValueError("PDF has no pages")
        page_count = pages_to_process(total, NUEXTRACT_MAX_PAGES_PER_REQUEST)
        pages: list[bytes] = []
        for i in range(page_count):
            page = doc.load_page(i)
            # Official NuExtract3-GGUF example: get_pixmap(dpi=…) → PNG bytes.
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
    max_edge_px: int | None = None

# https://huggingface.co/numind/NuExtract3-GGUF — pdf_to_png_data_urls(..., dpi=170)
REPODY_VLM_RENDER = ModelRenderPolicy(
    model_id="repody:vlm",
    doc_ref="numind/NuExtract3 (dpi=170 PNG; WebP→PNG for llama.cpp)",
    image_input="native_bytes",
    pdf_dpi=170,
    pdf_format="png",
    max_edge_px=None,
)

# Cloud API accepts original files; platform rasterization happens server-side.
REPODY_VLM_CLOUD_RENDER = ModelRenderPolicy(
    model_id="repody:vlm:cloud",
    doc_ref="nuextract.ai structured-extraction (upload original PDF/image)",
    image_input="native_bytes",
    pdf_dpi=170,
    pdf_format="png",
    max_edge_px=None,
)

RENDER_POLICIES: dict[str, ModelRenderPolicy] = {
    REPODY_VLM_RENDER.model_id: REPODY_VLM_RENDER,
    REPODY_VLM_CLOUD_RENDER.model_id: REPODY_VLM_CLOUD_RENDER,
}

# https://huggingface.co/zai-org/GLM-OCR — image + "Text Recognition:"
# Served via https://huggingface.co/ggml-org/GLM-OCR-GGUF
# Sampling/DPI from official SDK config (greedy; pdf_dpi=200; no edge cap).
GLM_OCR_RENDER = ModelRenderPolicy(
    model_id=GLM_OCR_CATALOG_ID,
    doc_ref="GLM-OCR (dpi=200 PNG; no edge-cap; image + 'Text Recognition:'; temp=0)",
    image_input="pil_rgb",
    pdf_dpi=GLM_OCR_PDF_DPI,
    pdf_format="png",
    max_edge_px=GLM_OCR_MAX_EDGE_PX,
)

RENDER_POLICIES[GLM_OCR_RENDER.model_id] = GLM_OCR_RENDER


def _is_pdf(mime_type: str, raw_bytes: bytes) -> bool:
    mime = (mime_type or "").lower()
    return mime == "application/pdf" or raw_bytes.startswith(b"%PDF")

def _is_image_upload(mime_type: str, raw_bytes: bytes) -> bool:
    if _is_pdf(mime_type, raw_bytes):
        return False
    mime = (mime_type or "").lower()
    return mime.startswith("image/")

def _is_webp(image_bytes: bytes) -> bool:
    return len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP"

def _webp_to_png_bytes(image_bytes: bytes) -> bytes:
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=False)
        return buf.getvalue()

def native_image_mime_type(mime_type: str, image_bytes: bytes) -> str:
    mime = (mime_type or "").lower()
    if mime == "image/png" or image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if mime in {"image/webp", "image/x-webp"} or _is_webp(image_bytes):
        return "image/webp"
    if mime in {"image/jpeg", "image/jpg"} or image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/jpeg"

def prepare_image_for_vlm(mime_type: str, image_bytes: bytes) -> tuple[bytes, str]:
    """Normalize image bytes for llama.cpp NuExtract vision."""
    detected = native_image_mime_type(mime_type, image_bytes)
    if detected == "image/webp":
        return _webp_to_png_bytes(image_bytes), "image/png"
    return image_bytes, detected

def repody_vlm_pages(
    bundle: DocumentBundle,
) -> tuple[list[tuple[bytes, str]], int]:
    """Pages for Repody VLM: prepared images; PDF → PNG @ official DPI.

    Second return value is the document page count (PDF total pages, or 1 for
    images) so callers can surface pages dropped beyond the NuExtract cap.
    """
    if _is_image_upload(bundle.mime_type, bundle.raw_bytes):
        bundle.page_count = 1
        page_bytes, mime = prepare_image_for_vlm(bundle.mime_type, bundle.raw_bytes)
        return [(page_bytes, mime)], 1

    if _is_pdf(bundle.mime_type, bundle.raw_bytes):
        pages, total_pages = render_nuextract_pdf_pages(bundle.raw_bytes)
        bundle.page_count = total_pages
        return [(page, "image/png") for page in pages], total_pages

    raise ValueError(
        f"Unsupported document type for NuExtract vision: {bundle.mime_type!r}. "
        "Upload a PDF or image (PNG, JPEG, WebP)."
    )

def cap_vlm_pages(pages: list[VlmPage], *, max_pages: int) -> tuple[list[VlmPage], int]:
    """Limit pages in one Repody VLM request; return (kept_pages, dropped_count)."""
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if len(pages) <= max_pages:
        return pages, 0
    return pages[:max_pages], len(pages) - max_pages

def pages_dropped(*, rendered: int, sent: int) -> int:
    """Pages not sent given document page count vs pages in the request."""
    return max(0, int(rendered) - int(sent))


def _resize_longest_edge_png(image_bytes: bytes, *, max_edge_px: int | None) -> bytes:
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as image:
        rgb = image.convert("RGB") if image.mode != "RGB" else image
        if max_edge_px is None:
            out = rgb
        else:
            width, height = rgb.size
            longest = max(width, height)
            if longest <= max_edge_px:
                out = rgb
            else:
                scale = max_edge_px / float(longest)
                out = rgb.resize(
                    (max(1, int(width * scale)), max(1, int(height * scale))),
                    Image.Resampling.LANCZOS,
                )
        buf = io.BytesIO()
        out.save(buf, format="PNG", optimize=False)
        return buf.getvalue()


def render_ocr_chat_pdf_pages(
    document_bytes: bytes,
    *,
    dpi: int,
    max_edge_px: int | None,
    max_pages: int,
) -> tuple[list[bytes], int]:
    """PDF → PNG pages for llama.cpp OCR chat adapters."""
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
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            png = pix.tobytes("png")
            pages.append(_resize_longest_edge_png(png, max_edge_px=max_edge_px))
        return pages, total
    finally:
        doc.close()


def prepare_image_for_ocr_chat(
    mime_type: str,
    image_bytes: bytes,
    *,
    max_edge_px: int | None,
) -> bytes:
    """Normalize to PNG; optionally cap longest edge."""
    detected = native_image_mime_type(mime_type, image_bytes)
    if detected == "image/webp":
        image_bytes = _webp_to_png_bytes(image_bytes)
    elif detected != "image/png":
        from PIL import Image

        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb = image.convert("RGB") if image.mode != "RGB" else image
            buf = io.BytesIO()
            rgb.save(buf, format="PNG", optimize=False)
            image_bytes = buf.getvalue()
    return _resize_longest_edge_png(image_bytes, max_edge_px=max_edge_px)


def ocr_chat_pages(
    bundle: DocumentBundle,
    *,
    dpi: int,
    max_edge_px: int | None,
    max_pages: int,
    label: str,
) -> tuple[list[bytes], int]:
    if _is_image_upload(bundle.mime_type, bundle.raw_bytes):
        bundle.page_count = 1
        return [
            prepare_image_for_ocr_chat(
                bundle.mime_type, bundle.raw_bytes, max_edge_px=max_edge_px
            )
        ], 1

    if _is_pdf(bundle.mime_type, bundle.raw_bytes):
        pages, total_pages = render_ocr_chat_pdf_pages(
            bundle.raw_bytes,
            dpi=dpi,
            max_edge_px=max_edge_px,
            max_pages=max_pages,
        )
        bundle.page_count = total_pages
        return pages, total_pages

    raise ValueError(
        f"Unsupported document type for {label}: {bundle.mime_type!r}. "
        "Upload a PDF or image (PNG, JPEG, WebP)."
    )


def glm_ocr_pages(bundle: DocumentBundle) -> tuple[list[bytes], int]:
    """Pages for GLM-OCR: PNG @ 200 DPI PDF; images kept full-res (no edge cap)."""
    return ocr_chat_pages(
        bundle,
        dpi=GLM_OCR_PDF_DPI,
        max_edge_px=GLM_OCR_MAX_EDGE_PX,
        max_pages=GLM_OCR_MAX_PAGES_PER_DOCUMENT,
        label="GLM-OCR",
    )


def _vlm_pages(bundle: DocumentBundle) -> tuple[list[VlmPage], int]:
    return repody_vlm_pages(bundle)

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
