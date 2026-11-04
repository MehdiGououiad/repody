"""Page images for NuExtract: PDF pages rendered to PNG at 170 DPI (official); images as is.

PDFs are rendered with PDFium (pypdfium2) and encoded with Pillow.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import pypdfium2 as pdfium

PDF_DPI = 170


def _png(page: pdfium.PdfPage) -> bytes:
    buffer = io.BytesIO()
    # `scale` is documented as a float; its default (1) makes type checkers read it as int.
    bitmap = page.render(scale=PDF_DPI / 72)  # pyright: ignore[reportArgumentType]
    bitmap.to_pil().save(buffer, format="PNG")
    return buffer.getvalue()


def page_images(
    data: bytes, mime: str, *, max_pages: int | None
) -> tuple[list[dict[str, Any]], int]:
    """``(image_url content parts, page count of the document)``; ``mime`` was checked on upload."""
    if mime == "application/pdf":
        with pdfium.PdfDocument(data) as pdf:
            total = len(pdf)
            if total == 0:
                raise ValueError("The PDF has no pages.")
            pages = [(_png(pdf[i]), "image/png") for i in range(min(total, max_pages or total))]
    elif mime.startswith("image/"):
        pages, total = [(data, mime)], 1
    else:
        raise ValueError("Unsupported document: upload a PDF or a PNG, JPEG or WebP image.")
    parts = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{m};base64,{base64.b64encode(b).decode()}"},
        }
        for b, m in pages
    ]
    return parts, total
