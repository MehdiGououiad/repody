"""Repody VLM extraction facade — warmup and extract live in submodules."""

from __future__ import annotations

from audit_workbench.extraction.repody_vlm_extract import extract_with_repody_vlm
from audit_workbench.extraction.repody_vlm_pages import (
    _encode_pages_for_vlm,
    _vlm_pages,
    cap_vlm_pages,
)
from audit_workbench.extraction.repody_vlm_payloads import (
    _fields_payload,
    _markdown_payload,
    _structured_payload,
    build_vlm_instructions,
    build_vlm_template,
    strip_vlm_thinking,
)
from audit_workbench.extraction.repody_vlm_warmup import warmup_repody_vlm

from audit_workbench.catalog.adapters import register_document_model_adapter
from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID

register_document_model_adapter(REPODY_VLM_CATALOG_ID, extract_with_repody_vlm)

__all__ = [
    "_encode_pages_for_vlm",
    "_fields_payload",
    "_markdown_payload",
    "_structured_payload",
    "_vlm_pages",
    "build_vlm_instructions",
    "build_vlm_template",
    "cap_vlm_pages",
    "extract_with_repody_vlm",
    "strip_vlm_thinking",
    "warmup_repody_vlm",
]
