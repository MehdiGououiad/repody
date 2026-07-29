from __future__ import annotations

import io

from PIL import Image

from repody.extraction.types import DocumentBundle
from repody.extraction.render import (
    REPODY_VLM_RENDER,
    prepare_nuextract_pages,
)


def test_render_policies_follow_upstream_docs():
    assert REPODY_VLM_RENDER.pdf_dpi == 170
    assert REPODY_VLM_RENDER.image_input == "native_bytes"
    assert not hasattr(REPODY_VLM_RENDER, "max_edge_px")


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
