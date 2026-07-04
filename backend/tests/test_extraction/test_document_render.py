from __future__ import annotations

from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.document_render import (
    REPODY_VLM_RENDER,
    repody_vlm_pages,
)


def test_render_policies_follow_upstream_docs():
    assert REPODY_VLM_RENDER.pdf_dpi == 170
    assert REPODY_VLM_RENDER.max_edge_px is None
    assert REPODY_VLM_RENDER.image_input == "native_bytes"


def test_repody_vlm_native_png_unchanged():
    from audit_workbench.settings import get_settings

    raw = b"\x89PNG\r\n\x1a\npixels"
    bundle = DocumentBundle(raw_bytes=raw, mime_type="image/png")
    pages, count = repody_vlm_pages(bundle, get_settings())
    assert pages == [(raw, "image/png")]
    assert count == 1
