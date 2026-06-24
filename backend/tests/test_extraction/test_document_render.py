from __future__ import annotations

from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.document_render import (
    REPODY_VLM_RENDER,
    SURYA_OCR_RENDER,
    repody_vlm_pages,
    surya_pil_pages,
)


def test_render_policies_follow_upstream_docs():
    assert REPODY_VLM_RENDER.pdf_dpi == 170
    assert REPODY_VLM_RENDER.max_edge_px is None
    assert REPODY_VLM_RENDER.image_input == "native_bytes"
    assert SURYA_OCR_RENDER.pdf_dpi == 96
    assert SURYA_OCR_RENDER.max_edge_px is None


def test_repody_vlm_native_png_unchanged():
    from audit_workbench.settings import get_settings

    raw = b"\x89PNG\r\n\x1a\npixels"
    bundle = DocumentBundle(raw_bytes=raw, mime_type="image/png")
    pages, count = repody_vlm_pages(bundle, get_settings())
    assert pages == [(raw, "image/png")]
    assert count == 1


def test_surya_native_image_no_resize(monkeypatch):
    from audit_workbench.settings import get_settings

    try:
        from PIL import Image
    except ImportError:
        return

    buf = __import__("io").BytesIO()
    Image.new("RGB", (400, 300), "white").save(buf, format="PNG")
    raw = buf.getvalue()
    bundle = DocumentBundle(raw_bytes=raw, mime_type="image/png")
    images = surya_pil_pages(bundle, get_settings())
    assert len(images) == 1
    assert images[0].size == (400, 300)
