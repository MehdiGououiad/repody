"""NuExtract Q4 vision extraction profile."""

from __future__ import annotations

import pytest

from audit_workbench.extraction.document_modes import (
    DOCUMENT_MODEL_READ_PATH_ID,
    resolve_read_path_for_document,
)
from audit_workbench.extraction.document_render import REPODY_VLM_RENDER
from audit_workbench.extraction.repody_vlm_payloads import _structured_payload
from audit_workbench.catalog.registry import parse_document_model
from audit_workbench.extraction.repody_vlm import REPODY_VLM_CATALOG_ID
from audit_workbench.extraction.base import SchemaFieldSpec


def test_read_paths_resolve_to_nuextract_vision():
    _, used = resolve_read_path_for_document(DOCUMENT_MODEL_READ_PATH_ID)
    assert used == DOCUMENT_MODEL_READ_PATH_ID
    _, used_default = resolve_read_path_for_document(None)
    assert used_default == DOCUMENT_MODEL_READ_PATH_ID


def test_legacy_read_paths_rejected():
    for mode in ("pdf_text", "auto", "vlm"):
        with pytest.raises(ValueError, match="Unknown read path"):
            resolve_read_path_for_document(mode)


def test_nuextract_official_render_policy():
    policy = REPODY_VLM_RENDER
    assert policy.pdf_dpi == 170
    assert policy.pdf_format == "png"


def test_nuextract_payload_official_generation_defaults():
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    schema = [SchemaFieldSpec(name="invoice_number", template_type="verbatim-string")]
    payload = _structured_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        schema=schema,
        extraction_instructions="",
    )
    assert payload["temperature"] == 0.2
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
