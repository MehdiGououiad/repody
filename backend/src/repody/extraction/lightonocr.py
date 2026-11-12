"""Markdown transcription with LightOnOCR-3, sent as the model card's vLLM example sends it.

Source: https://huggingface.co/lightonai/LightOnOCR-3-4B ("Usage with vLLM"):

- PDF pages rendered at 400 DPI, then ``thumbnail((2048, 2048))``: at most 2048 px on the
  longest edge, aspect ratio kept, never upscaled; images get the same ``thumbnail``;
- one request per page, the PNG image alone (transcription mode); thinking off, which the card
  sets on the server (``--default-chat-template-kwargs``) and Repody sends per request;
- ``max_tokens`` 4096, temperature 0.2, top_p 0.9.
"""

from typing import Any

from repody.extraction import render

PDF_DPI = 400
LONGEST_EDGE = 2048
MAX_TOKENS = 4096
TEMPERATURE = 0.2
TOP_P = 0.9


def page_parts(
    data: bytes, mime: str, *, max_pages: int | None
) -> tuple[list[dict[str, Any]], int]:
    """``(one image part per page, page count)``; ``mime`` was checked on upload."""
    if mime == "application/pdf":
        pages, total = render.pdf_pages(data, max_pages=max_pages, dpi=PDF_DPI)
    else:
        pages, total = [render.open_image(data)], 1
    for page in pages:
        page.thumbnail((LONGEST_EDGE, LONGEST_EDGE))  # in place; never upscales
    return [render.image_part(page) for page in pages], total


def request(model: str) -> dict[str, Any]:
    """Request body; the page image goes in the user message."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "messages": [{"role": "user", "content": []}],
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }
