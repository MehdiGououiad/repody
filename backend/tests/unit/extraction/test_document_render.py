from __future__ import annotations

import io

from PIL import Image

from repody.extraction.nuextract import NUEXTRACT_PDF_DPI
from repody.extraction.render import prepare_nuextract_pages
from repody.extraction.types import DocumentBundle


def test_pdf_dpi_follows_upstream_docs():
    assert NUEXTRACT_PDF_DPI == 170


def test_nuextract_native_png_unchanged():
    raw = b"\x89PNG\r\n\x1a\npixels"
    bundle = DocumentBundle(raw_bytes=raw, mime_type="image/png")
    pages, count = prepare_nuextract_pages(bundle)
    assert pages == [(raw, "image/png")]
    assert count == 1


def test_nuextract_passes_webp_through():
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(12, 34, 56)).save(buf, format="WEBP")
    webp = buf.getvalue()
    assert webp[:4] == b"RIFF" and webp[8:12] == b"WEBP"

    pages, count = prepare_nuextract_pages(DocumentBundle(raw_bytes=webp, mime_type="image/webp"))
    assert count == 1
    assert pages == [(webp, "image/webp")]
