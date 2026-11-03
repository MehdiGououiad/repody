"""NuExtract Q4 vision extraction profile."""

from __future__ import annotations

from repody.extraction.nuextract import NUEXTRACT_PDF_DPI, structured_chat_payload
from repody.extraction.types import SchemaFieldSpec
from repody.settings import get_settings


def test_nuextract_official_pdf_dpi():
    assert NUEXTRACT_PDF_DPI == 170


def test_nuextract_payload_official_generation_defaults():
    model = get_settings().llamacpp_served_model
    schema = [SchemaFieldSpec(name="invoice_number", template_type="verbatim-string")]
    payload = structured_chat_payload(
        model=model,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        schema=schema,
        extraction_instructions="",
    )
    assert payload["temperature"] == 0.2
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
