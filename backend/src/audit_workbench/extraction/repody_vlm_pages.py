from __future__ import annotations

import base64
from typing import Any

from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.document_render import repody_vlm_pages as _render_repody_vlm_pages

type VlmPage = tuple[bytes, str]


def cap_vlm_pages(pages: list[bytes], *, max_pages: int) -> tuple[list[bytes], int]:
    """Limit pages in one Repody VLM request; return (kept_pages, dropped_count)."""
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if len(pages) <= max_pages:
        return pages, 0
    return pages[:max_pages], len(pages) - max_pages


def _vlm_pages(bundle: DocumentBundle) -> tuple[list[VlmPage], int]:
    return _render_repody_vlm_pages(bundle)


def _encode_pages_for_vlm(pages: list[VlmPage]) -> list[dict[str, Any]]:
    return [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64.b64encode(page).decode('ascii')}"
            },
        }
        for page, mime_type in pages
    ]
