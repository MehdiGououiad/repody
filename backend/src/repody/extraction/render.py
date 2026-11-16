"""Page images for the models, as OpenAI ``image_url`` content parts (base64 data URLs).

PDF pages are rendered with PDFium (pypdfium2); Pillow decodes and encodes images. The same
decoders tell what an upload is (``file_type``): a file is a PDF or an image only if they
can open it, whatever its name or declared type.

PDFium is not thread-safe (pypdfium2 docs, "Incompatibility with threading"), and documents
are rendered in worker threads, so every PDFium call holds ``_PDFIUM``.
"""

import base64
import io
import threading
from typing import Any, BinaryIO

import pypdfium2 as pdfium
from PIL import Image, ImageOps

PDF_DPI = 170  # NuExtract3's documented rendering resolution
# A page renders to at most this many pixels: an oversized page (a PDF can declare one of
# 200 x 200 inches) is drawn smaller instead of filling the worker's memory.
MAX_RENDER_PIXELS = 4096 * 4096
IMAGE_FORMATS = ("PNG", "JPEG", "WEBP")
PDF = "application/pdf"

_PDFIUM = threading.Lock()


def file_type(file: BinaryIO) -> str | None:
    """The MIME type of a PDF, PNG, JPEG or WebP file, or None when neither PDFium nor
    Pillow opens it. The stream is read from the start and rewound."""
    try:
        file.seek(0)
        try:
            with Image.open(file, formats=IMAGE_FORMATS) as image:
                image.verify()
                return Image.MIME[image.format or ""]
        except OSError, SyntaxError, KeyError:  # UnidentifiedImageError is an OSError
            pass
        file.seek(0)
        try:
            with _PDFIUM, pdfium.PdfDocument(file):
                return PDF
        except pdfium.PdfiumError:
            return None
    finally:
        file.seek(0)


def _render(page: pdfium.PdfPage, dpi: int) -> Image.Image:
    """The page at ``dpi``, or smaller when that would exceed MAX_RENDER_PIXELS."""
    width, height = page.get_size()  # PDF points, 1/72 inch
    scale = min(dpi / 72, (MAX_RENDER_PIXELS / max(width * height, 1)) ** 0.5)
    # `scale` is documented as a float; its default (1) makes type checkers read it as int.
    return page.render(scale=scale).to_pil()  # pyright: ignore[reportArgumentType]


def pdf_page_parts(data: bytes, *, max_pages: int | None) -> tuple[list[dict[str, Any]], int]:
    """``(image parts, page count)``: the pages at NuExtract3's 170 DPI, each encoded as soon as
    it is drawn, so one page's bitmap is in memory at a time (an A4 page is ~8 MB raw, a few
    hundred KB as PNG)."""
    with _PDFIUM, pdfium.PdfDocument(data) as pdf:
        total = len(pdf)
        count = min(total, max_pages or total)
        parts = [image_part(_render(pdf[index], PDF_DPI)) for index in range(count)]
    return parts, total


def open_image(data: bytes) -> Image.Image:
    """An uploaded image as the model should see it: upright by its EXIF orientation (phone
    photos), transparency on white, RGB. llama.cpp decodes images with stb_image, which ignores
    EXIF and cannot read WebP, so images are sent re-encoded as PNG, as the NuExtract3 model card
    sends them (lossless: the model gets exactly these pixels)."""
    with Image.open(io.BytesIO(data)) as image:
        upright = ImageOps.exif_transpose(image)
        if upright.mode in ("RGBA", "LA") or "transparency" in upright.info:
            rgba = upright.convert("RGBA")
            page = Image.new("RGB", rgba.size, "white")
            page.paste(rgba, mask=rgba.getchannel("A"))
            return page
        return upright.convert("RGB")


def image_part(image: Image.Image | bytes, mime: str = "image/png") -> dict[str, Any]:
    """A content part for a Pillow image (sent as PNG) or encoded image bytes of ``mime``."""
    if isinstance(image, Image.Image):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image, mime = buffer.getvalue(), "image/png"
    url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    return {"type": "image_url", "image_url": {"url": url}}


SCREEN_DPI = 110  # pages shown beside a report: sharp on screen, a fraction of the model's size


def page_preview(data: bytes, mime: str, index: int) -> bytes | None:
    """Page ``index`` (from 0) of an uploaded PDF or image as WebP for the screen, or None when
    the document has no such page."""
    if mime == PDF:
        with _PDFIUM, pdfium.PdfDocument(data) as pdf:
            if not 0 <= index < len(pdf):
                return None
            image = _render(pdf[index], SCREEN_DPI)
    elif index == 0:
        image = open_image(data)
    else:
        return None
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=82)
    return buffer.getvalue()
