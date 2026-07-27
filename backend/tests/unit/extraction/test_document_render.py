from __future__ import annotations

import io

from PIL import Image

from audit_workbench.extraction.types import DocumentBundle
from audit_workbench.extraction.render import (
    REPODY_VLM_RENDER,
    prepare_image_for_vlm,
    repody_vlm_pages,
)


def test_render_policies_follow_upstream_docs():
    assert REPODY_VLM_RENDER.pdf_dpi == 170
    assert REPODY_VLM_RENDER.max_edge_px is None
    assert REPODY_VLM_RENDER.image_input == "native_bytes"


def test_repody_vlm_native_png_unchanged():
    raw = b"\x89PNG\r\n\x1a\npixels"
    bundle = DocumentBundle(raw_bytes=raw, mime_type="image/png")
    pages, count = repody_vlm_pages(bundle)
    assert pages == [(raw, "image/png")]
    assert count == 1


def test_prepare_image_converts_webp_to_png():
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(12, 34, 56)).save(buf, format="WEBP")
    webp = buf.getvalue()
    assert webp[:4] == b"RIFF" and webp[8:12] == b"WEBP"

    out, mime = prepare_image_for_vlm("image/webp", webp)
    assert mime == "image/png"
    assert out.startswith(b"\x89PNG\r\n\x1a\n")

    pages, count = repody_vlm_pages(DocumentBundle(raw_bytes=webp, mime_type="image/webp"))
    assert count == 1
    assert pages[0][1] == "image/png"
    assert pages[0][0].startswith(b"\x89PNG\r\n\x1a\n")
