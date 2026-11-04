"""Page images for NuExtract: PDF pages rendered to PNG at 170 DPI (official); images as is."""

from __future__ import annotations

import base64
from typing import Any

import pymupdf

PDF_DPI = 170


def page_images(
    data: bytes, mime: str, *, max_pages: int | None
) -> tuple[list[dict[str, Any]], int]:
    """``(image_url content parts, page count of the document)``; ``mime`` was checked on upload."""
    if mime == "application/pdf":
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            total = len(pdf)
            if total == 0:
                raise ValueError("The PDF has no pages.")
            pages = [
                (pdf[i].get_pixmap(dpi=PDF_DPI, alpha=False).tobytes("png"), "image/png")
                for i in range(min(total, max_pages or total))
            ]
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
