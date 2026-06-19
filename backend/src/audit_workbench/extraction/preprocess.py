from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from audit_workbench.settings import Settings


def _resize_for_cpu(image, max_edge: int | None):
    from PIL import Image

    if not max_edge:
        return image
    w, h = image.size
    if max(w, h) <= max_edge:
        return image
    scale = max_edge / max(w, h)
    return image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)


def _to_jpeg_bytes(image, quality: int = 82, *, optimize: bool = True) -> bytes:
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality, optimize=optimize)
    return buf.getvalue()


def _to_png_bytes(image) -> bytes:
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _pdf_page_images(document_bytes: bytes, *, dpi: int, max_pages: int, hard_cap: int):
    """Rasterize PDF pages to PIL images (up to configured page limits)."""
    import fitz
    from PIL import Image

    from audit_workbench.extraction.pdf_pages import pages_to_process

    doc = fitz.open(stream=document_bytes, filetype="pdf")
    page_count = pages_to_process(len(doc), max_pages, hard_cap=hard_cap)
    scale = dpi / 72.0
    images = []
    for i in range(page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    doc.close()
    if not images:
        raise ValueError("PDF has no pages")
    return images


def render_pdf_pages_png(
    document_bytes: bytes,
    *,
    settings: Settings,
    dpi: int,
    max_edge: int | None = None,
) -> list[bytes]:
    """Render PDF pages as lossless PNG for OCR engines that benefit from fidelity."""
    cfg = settings
    images = _pdf_page_images(
        document_bytes,
        dpi=dpi,
        max_pages=cfg.ocr_max_pages,
        hard_cap=cfg.ocr_max_pages_hard_cap,
    )
    return [_to_png_bytes(_resize_for_cpu(image, max_edge)) for image in images]


def render_document_pages_jpeg(
    document_bytes: bytes,
    mime_type: str,
    *,
    settings: Settings,
) -> list[bytes]:
    """Render each PDF page (up to document_render_max_pages) as its own JPEG."""
    from audit_workbench.settings import get_settings

    cfg = settings or get_settings()
    max_edge = cfg.document_render_max_edge_px
    max_pages = cfg.ocr_max_pages
    hard_cap = cfg.ocr_max_pages_hard_cap
    dpi = cfg.document_render_pdf_dpi

    mime = (mime_type or "").lower()
    if mime == "application/pdf" or document_bytes[:4] == b"%PDF":
        images = _pdf_page_images(
            document_bytes,
            dpi=dpi,
            max_pages=max_pages,
            hard_cap=hard_cap,
        )
        return [
            _to_jpeg_bytes(
                _resize_for_cpu(image, max_edge),
                quality=cfg.ocr_jpeg_quality,
                optimize=cfg.ocr_jpeg_optimize,
            )
            for image in images
        ]

    from PIL import Image

    image = Image.open(io.BytesIO(document_bytes))
    image.load()
    image = _resize_for_cpu(image, max_edge)
    return [
        _to_jpeg_bytes(
            image,
            quality=cfg.ocr_jpeg_quality,
            optimize=cfg.ocr_jpeg_optimize,
        )
    ]
