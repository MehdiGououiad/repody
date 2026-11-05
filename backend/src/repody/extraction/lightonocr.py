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

from typing import Any

from PIL import Image

from repody.extraction import render

LONGEST_EDGE = 2048
TEMPERATURE = 0.2
TOP_P = 1.0


def page_parts(
    data: bytes, mime: str, *, max_pages: int | None
) -> tuple[list[dict[str, Any]], int]:
    """``(one image part per page, page count)``; ``mime`` was checked on upload."""
    if mime == "application/pdf":
        pages, total = render.pdf_pages(data, max_pages=max_pages, longest_edge=LONGEST_EDGE)
    else:
        image = render.open_image(data)
        image.thumbnail((LONGEST_EDGE, LONGEST_EDGE), Image.Resampling.LANCZOS)  # never upscales
        pages, total = [image], 1
    return [render.image_part(page) for page in pages], total


def request(model: str) -> dict[str, Any]:
    """Request body; the page image goes in the user message."""
    return {
        "model": model,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "messages": [{"role": "user", "content": []}],
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }
