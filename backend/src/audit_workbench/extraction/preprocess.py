from __future__ import annotations

import io

from audit_workbench.extraction.nuextract_contract import (
    NUEXTRACT_MAX_PAGES_PER_REQUEST,
    NUEXTRACT_PDF_DPI,
)


def _to_png_bytes(image) -> bytes:
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _pdf_page_images(document_bytes: bytes, *, dpi: int, max_pages: int) -> list:
    """Rasterize PDF pages to PIL images (up to max_pages)."""
    import fitz
    from PIL import Image

    from audit_workbench.extraction.pdf_pages import pages_to_process

    doc = fitz.open(stream=document_bytes, filetype="pdf")
    page_count = pages_to_process(len(doc), max_pages)
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


def render_nuextract_pdf_pages(document_bytes: bytes) -> list[bytes]:
    """Official NuExtract PDF input: lossless PNG @ 170 DPI, up to 6 pages."""
    images = _pdf_page_images(
        document_bytes,
        dpi=NUEXTRACT_PDF_DPI,
        max_pages=NUEXTRACT_MAX_PAGES_PER_REQUEST,
    )
    return [_to_png_bytes(image) for image in images]
