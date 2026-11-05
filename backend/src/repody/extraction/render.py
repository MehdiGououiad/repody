"""Page images for the models, as OpenAI ``image_url`` content parts (base64 data URLs).

PDF pages are rendered with PDFium (pypdfium2); Pillow decodes and encodes images.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import pypdfium2 as pdfium
from PIL import Image

PDF_DPI = 170  # NuExtract3's documented rendering resolution


def pdf_pages(
    data: bytes, *, max_pages: int | None, longest_edge: int | None = None
) -> tuple[list[Image.Image], int]:
    """``(rendered pages, page count)``: at 170 DPI, or fitted to ``longest_edge`` pixels."""
    with pdfium.PdfDocument(data) as pdf:
        total = len(pdf)
        pages = []
        for index in range(min(total, max_pages or total)):
            page = pdf[index]
            scale = longest_edge / max(page.get_size()) if longest_edge else PDF_DPI / 72
            # `scale` is documented as a float; its default (1) makes type checkers read it as int.
            pages.append(page.render(scale=scale).to_pil())  # pyright: ignore[reportArgumentType]
    return pages, total


def open_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def image_part(image: Image.Image | bytes, mime: str = "image/png") -> dict[str, Any]:
    """A content part for a Pillow image (sent as PNG) or encoded image bytes of ``mime``."""
    if isinstance(image, Image.Image):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image, mime = buffer.getvalue(), "image/png"
    url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    return {"type": "image_url", "image_url": {"url": url}}
