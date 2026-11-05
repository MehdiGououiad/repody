"""Markdown transcription with LightOnOCR-3, sent the way LightOn's official client sends it.

Source: github.com/lightonai/LightOnOCR at 36755d4 (lightonocr/client.py, render.py, models.py) and
the lightonai/LightOnOCR-3-4B model card:

- each page at most 2048 px on its longest edge: PDF pages rendered at that size, images
  downscaled with their aspect ratio kept, never upscaled;
- one request per page, the image alone (transcription mode), thinking off;
- temperature 0.2 and top_p 1.0 (the client's LightOnOCR-3 profile).

The client's optional escaped-math repair (``fix_dollars``) is not applied: the text is the
model's own, as with ``fix_dollars=False``.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import pypdfium2 as pdfium
from PIL import Image

LONGEST_EDGE = 2048
TEMPERATURE = 0.2
TOP_P = 1.0


def page_images(data: bytes, mime: str, *, max_pages: int | None) -> tuple[list[Image.Image], int]:
    """``(pages sized for the model, page count of the document)``; ``mime`` was checked on upload."""
    if mime == "application/pdf":
        with pdfium.PdfDocument(data) as pdf:
            total = len(pdf)
            pages = []
            for index in range(min(total, max_pages or total)):
                width, height = pdf[index].get_size()
                bitmap = pdf[index].render(scale=LONGEST_EDGE / max(width, height))  # pyright: ignore[reportArgumentType]
                pages.append(bitmap.to_pil().convert("RGB"))
        return pages, total
    image = Image.open(io.BytesIO(data)).convert("RGB")
    image.thumbnail((LONGEST_EDGE, LONGEST_EDGE), Image.Resampling.LANCZOS)  # never upscales
    return [image], 1


def request(model: str) -> dict[str, Any]:
    """Request body without the page image (``messages[0]["content"]`` gets it)."""
    return {
        "model": model,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "messages": [{"role": "user", "content": []}],
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }


def image_part(image: Image.Image) -> dict[str, Any]:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    return {"type": "image_url", "image_url": {"url": url}}
