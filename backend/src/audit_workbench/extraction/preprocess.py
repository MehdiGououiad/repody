from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from audit_workbench.settings import Settings


def _resize_for_cpu(image, max_edge: int):
    from PIL import Image

    w, h = image.size
    if max(w, h) <= max_edge:
        return image
    scale = max_edge / max(w, h)
    return image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)


def _to_jpeg_bytes(image, quality: int = 82) -> bytes:
    from PIL import Image

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def render_document_pages_jpeg(
    document_bytes: bytes,
    mime_type: str,
    *,
    settings: Settings,
) -> list[bytes]:
    """Render each PDF page (up to ocr_max_pages) as its own JPEG for per-page OCR."""
    from audit_workbench.extraction.pdf_pages import pages_to_process
    from audit_workbench.settings import get_settings

    cfg = settings or get_settings()
    max_edge = cfg.ocr_max_edge_px
    max_pages = cfg.ocr_max_pages
    hard_cap = cfg.ocr_max_pages_hard_cap
    dpi = cfg.ocr_pdf_dpi
    scale = dpi / 72.0

    mime = (mime_type or "").lower()
    if mime == "application/pdf" or document_bytes[:4] == b"%PDF":
        import fitz

        doc = fitz.open(stream=document_bytes, filetype="pdf")
        page_count = pages_to_process(len(doc), max_pages, hard_cap=hard_cap)
        pages: list[bytes] = []
        for i in range(page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            from PIL import Image

            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            image = _resize_for_cpu(image, max_edge)
            pages.append(_to_jpeg_bytes(image, quality=cfg.ocr_jpeg_quality))
        doc.close()
        if not pages:
            raise ValueError("PDF has no pages")
        return pages

    from PIL import Image

    image = Image.open(io.BytesIO(document_bytes))
    image.load()
    image = _resize_for_cpu(image, max_edge)
    return [_to_jpeg_bytes(image, quality=cfg.ocr_jpeg_quality)]


def render_document_to_jpeg(
    document_bytes: bytes,
    mime_type: str,
    *,
    settings: Settings,
) -> bytes:
    """Convert PDF/image input to a single CPU-optimized JPEG page (bytes only)."""
    from audit_workbench.extraction.pdf_pages import pages_to_process
    from audit_workbench.settings import get_settings

    cfg = settings or get_settings()
    max_edge = cfg.ocr_max_edge_px
    max_pages = cfg.ocr_max_pages
    hard_cap = cfg.ocr_max_pages_hard_cap
    dpi = cfg.ocr_pdf_dpi
    scale = dpi / 72.0

    mime = (mime_type or "").lower()
    if mime == "application/pdf" or document_bytes[:4] == b"%PDF":
        import fitz

        doc = fitz.open(stream=document_bytes, filetype="pdf")
        page_count = pages_to_process(len(doc), max_pages, hard_cap=hard_cap)
        images = []
        for i in range(page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            from PIL import Image

            images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        doc.close()
        if not images:
            raise ValueError("PDF has no pages")
        from PIL import Image

        combined = images[0] if len(images) == 1 else _stack_pages(images)
    else:
        from PIL import Image

        combined = Image.open(io.BytesIO(document_bytes))
        combined.load()

    combined = _resize_for_cpu(combined, max_edge)
    return _to_jpeg_bytes(combined, quality=cfg.ocr_jpeg_quality)


def document_to_image_bytes(
    document_bytes: bytes,
    mime_type: str,
    *,
    settings: Settings,
) -> tuple[bytes, str]:
    """Convert PDF/image input to a single CPU-optimized JPEG page."""
    jpeg = render_document_to_jpeg(document_bytes, mime_type, settings=settings)
    return jpeg, "image/jpeg"


def _stack_pages(images):
    from PIL import Image

    width = max(img.width for img in images)
    height = sum(img.height for img in images)
    canvas = Image.new("RGB", (width, height), "white")
    y = 0
    for img in images:
        if img.mode != "RGB":
            img = img.convert("RGB")
        canvas.paste(img, (0, y))
        y += img.height
    return canvas
