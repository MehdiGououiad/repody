"""Page images for the models, as OpenAI ``image_url`` content parts (base64 data URLs).

PDF pages are rendered with PDFium (pypdfium2); Pillow decodes and encodes images. The same
decoders tell what an upload is (``inspect``): a file is a PDF or an image only if they
can open it, whatever its name or declared type.

PDFium is not thread-safe (pypdfium2 docs, "Incompatibility with threading"), and documents
are rendered in worker threads, so every PDFium call holds ``_PDFIUM``.
"""

import base64
import io
import math
import threading
from dataclasses import dataclass
from typing import Any, BinaryIO

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image, ImageOps

PDF_DPI = 170  # NuExtract3's documented rendering resolution
# Every page reaches the model with at least this many pixels: about an A4 page at PDF_DPI (2.8 MP),
# the input the model card benchmarks. Smaller pages (A5, A6 or receipt PDFs, photos, ID cards,
# screenshots) are drawn or enlarged to it. Measured on staging (24 November, six small documents,
# 5 reads each): 89.5 % of values right at the model server's own 1 MP floor, 99.0 % at 3 MP.
MIN_MODEL_PIXELS = 3_000_000
# A page renders to at most this many pixels: an oversized page (a PDF can declare one of
# 200 x 200 inches) is drawn smaller instead of filling the worker's memory.
MAX_RENDER_PIXELS = 4096 * 4096
# Pillow refuses, from the header and before decoding, an image over twice this (an "image
# bomb": a small PNG that would decode to gigabytes); a 48 MP phone photo is under it.
Image.MAX_IMAGE_PIXELS = 32_000_000
IMAGE_FORMATS = ("PNG", "JPEG", "WEBP")
PDF = "application/pdf"

_PDFIUM = threading.Lock()


class LockedPdfError(ValueError):
    """A PDF that needs a password to open: Repody cannot read it, and says so."""


@dataclass(frozen=True, slots=True)
class FileInfo:
    mime: str
    pages: int  # a PDF's pages, 1 for an image
    # Each page's pixels as the model gets it (see model_size), for its token count.
    page_pixels: tuple[int, ...] = ()


def _scale(width: float, height: float, dpi: int, min_pixels: int = 0) -> float:
    """The scale a page of ``width`` x ``height`` points (or pixels, at ``dpi`` 72) is drawn at:
    ``dpi``, larger when that gives fewer than ``min_pixels``, and never past MAX_RENDER_PIXELS."""
    area = max(width * height, 1)
    return min(max(dpi / 72, (min_pixels / area) ** 0.5), (MAX_RENDER_PIXELS / area) ** 0.5)


def model_size(width: float, height: float, dpi: int = 72, area: float = 1.0) -> tuple[int, int]:
    """The pixel size a page of ``width`` x ``height`` (points at ``dpi`` 72 for a PDF page, pixels
    for an image) is sent to the model at: at least MIN_MODEL_PIXELS, at most MAX_RENDER_PIXELS,
    then times ``area`` (a second read is sent at another size, repody.extraction.pipeline)."""
    scale = _scale(width, height, dpi, MIN_MODEL_PIXELS) * area**0.5
    return max(1, round(width * scale)), max(1, round(height * scale))


def inspect(file: BinaryIO) -> FileInfo | None:
    """What a PDF, PNG, JPEG or WebP file is, its page count and page sizes, from its headers (no
    page is decoded); None when neither PDFium nor Pillow opens it. The stream is read from the start
    and rewound. Raises LockedPdfError for a password-protected PDF. Blocking (PDFium holds a
    process-wide lock): call it in a thread."""
    try:
        file.seek(0)
        try:
            with Image.open(file, formats=IMAGE_FORMATS) as image:
                image.verify()
                width, height = model_size(image.width, image.height)
                return FileInfo(Image.MIME[image.format or ""], 1, (width * height,))
        except Image.DecompressionBombError:
            return None
        except OSError, SyntaxError, KeyError:  # UnidentifiedImageError is an OSError
            pass
        file.seek(0)
        try:
            with _PDFIUM, pdfium.PdfDocument(file) as pdf:
                sizes = [pdf.get_page_size(index) for index in range(len(pdf))]
            pixels = tuple(math.prod(model_size(w, h, PDF_DPI)) for w, h in sizes)
            return FileInfo(PDF, len(sizes), pixels)
        except pdfium.PdfiumError as error:
            if getattr(error, "err_code", None) == pdfium_c.FPDF_ERR_PASSWORD:
                raise LockedPdfError from error
            return None
    finally:
        file.seek(0)


def _render(page: pdfium.PdfPage, scale: float) -> Image.Image:
    # `scale` is documented as a float; its default (1) makes type checkers read it as int.
    return page.render(scale=scale).to_pil()  # pyright: ignore[reportArgumentType]


def _screen(page: pdfium.PdfPage, dpi: int) -> Image.Image:
    """The page at ``dpi``, or smaller when that would exceed MAX_RENDER_PIXELS."""
    width, height = page.get_size()  # PDF points, 1/72 inch
    return _render(page, _scale(width, height, dpi))


def _for_model(page: pdfium.PdfPage, area: float) -> Image.Image:
    """The page as the model gets it (``model_size``): drawn at that size, so small text stays
    sharp instead of being enlarged as a bitmap."""
    width, height = page.get_size()
    return _render(page, _scale(width, height, PDF_DPI, MIN_MODEL_PIXELS) * area**0.5)


def pdf_page_parts(
    data: bytes, *, max_pages: int | None, area: float = 1.0
) -> tuple[list[dict[str, Any]], int]:
    """``(image parts, page count)``: the pages at NuExtract3's 170 DPI, or larger for a page
    under MIN_MODEL_PIXELS (``model_size``), each encoded as soon as it is drawn, so one page's
    bitmap is in memory at a time (an A4 page is ~8 MB raw, a few hundred KB as PNG)."""
    with _PDFIUM, pdfium.PdfDocument(data) as pdf:
        total = len(pdf)
        count = min(total, max_pages or total)
        parts = [image_part(_for_model(pdf[index], area)) for index in range(count)]
    return parts, total


def open_image(data: bytes) -> Image.Image:
    """An uploaded image as the model should see it: upright by its EXIF orientation (phone
    photos), transparency on white, RGB. llama.cpp decodes images with stb_image, which ignores
    EXIF and cannot read WebP, so images are sent re-encoded as PNG, as the NuExtract3 model card
    sends them (lossless: the model gets exactly these pixels)."""
    with Image.open(io.BytesIO(data)) as image:
        scale = (MAX_RENDER_PIXELS / (image.width * image.height)) ** 0.5
        if scale < 1:  # drawn smaller, like an oversized PDF page (JPEG decodes at that size)
            image.thumbnail((int(image.width * scale), int(image.height * scale)))
        upright = ImageOps.exif_transpose(image)
        if upright.mode in ("RGBA", "LA") or "transparency" in upright.info:
            rgba = upright.convert("RGBA")
            page = Image.new("RGB", rgba.size, "white")
            page.paste(rgba, mask=rgba.getchannel("A"))
            return page
        return upright.convert("RGB")


def model_image(image: Image.Image, area: float = 1.0) -> Image.Image:
    """An upright image (``open_image``) at the size the model gets it (``model_size``): a small
    photo or scan is enlarged (bicubic, as the model's own image processor resizes)."""
    size = model_size(image.width, image.height, area=area)
    return image if size == image.size else image.resize(size, Image.Resampling.BICUBIC)


def image_part(image: Image.Image) -> dict[str, Any]:
    """A content part for a Pillow image, sent as a PNG data URL."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    url = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    return {"type": "image_url", "image_url": {"url": url}}


SCREEN_DPI = 110  # pages shown beside a report: sharp on screen, a fraction of the model's size


def page_preview(data: bytes, mime: str, index: int) -> bytes | None:
    """Page ``index`` (from 0) of an uploaded PDF or image as WebP for the screen, or None when
    the document has no such page."""
    if mime == PDF:
        with _PDFIUM, pdfium.PdfDocument(data) as pdf:
            if not 0 <= index < len(pdf):
                return None
            image = _screen(pdf[index], SCREEN_DPI)
    elif index == 0:
        image = open_image(data)
    else:
        return None
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=82)
    return buffer.getvalue()
