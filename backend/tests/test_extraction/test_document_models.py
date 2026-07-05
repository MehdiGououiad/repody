from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from audit_workbench.extraction.base import ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.field_json import parse_fields_json
from audit_workbench.extraction.document_model_branding import (
    REPODY_VLM_CATALOG_ID,
    UnknownCatalogIdError,
)
from audit_workbench.catalog.registry import (
    normalize_model_id,
    parse_document_model,
)
from audit_workbench.extraction.repody_vlm import (
    _encode_pages_for_vlm,
    _fields_payload,
    _markdown_payload,
    _structured_payload,
    _vlm_pages,
    build_vlm_instructions,
    build_vlm_template,
    cap_vlm_pages,
    strip_vlm_thinking,
)


def test_catalog_routes_repody_vlm_to_docker_model_runner():
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.runtime == "docker_model_runner"
    assert spec.engine == "document_model"


def test_unknown_model_id_raises():
    with pytest.raises(UnknownCatalogIdError, match="unknown-model"):
        normalize_model_id("unknown-model")


def test_repody_vlm_template_and_flat_json_normalize_money():
    schema = [
        SchemaFieldSpec(name="total_amount", description="Total TTC", template_type="number"),
        SchemaFieldSpec(name="invoice_number", description="Invoice reference"),
    ]

    assert build_vlm_template(schema) == {
        "total_amount": "number",
        "invoice_number": "verbatim-string",
    }

    instructions = build_vlm_instructions(schema, document_instructions="Use ISO dates.")
    assert "Field instructions:" in instructions
    assert "total_amount" in instructions
    assert "Total TTC" in instructions
    assert "`invoice_number`" in instructions
    assert "Use ISO dates." in instructions

    wrapped = _fields_payload(
        '{"total_amount": 6000.0, "invoice_number": "FAC-42"}',
        schema,
    )
    fields = parse_fields_json(wrapped, schema)
    assert fields[0].value == "6000.00"
    assert fields[1].value == "FAC-42"


def test_repody_vlm_template_uses_explicit_nuextract_type():
    schema = [
        SchemaFieldSpec(name="invoice_date", description="", template_type="date"),
        SchemaFieldSpec(name="contact", description="", template_type="email-address"),
    ]
    assert build_vlm_template(schema) == {
        "invoice_date": "date",
        "contact": "email-address",
    }


def test_cap_vlm_pages_truncates_extra_pages():
    pages = [b"page-1", b"page-2", b"page-3"]
    kept, dropped = cap_vlm_pages(pages, max_pages=2)
    assert kept == [b"page-1", b"page-2"]
    assert dropped == 1


def test_cap_vlm_pages_keeps_all_when_under_limit():
    pages = [b"page-1"]
    kept, dropped = cap_vlm_pages(pages, max_pages=4)
    assert kept == pages
    assert dropped == 0


def test_repody_vlm_preserves_png_upload_bytes():
    from audit_workbench.settings import get_settings

    bundle = DocumentBundle(raw_bytes=b"\x89PNG\r\n\x1a\nimage-bytes", mime_type="image/png")

    pages, pages_rendered = _vlm_pages(bundle, get_settings())

    assert pages == [(bundle.raw_bytes, "image/png")]
    assert pages_rendered == 1
    assert bundle.page_count == 1


def test_repody_vlm_renders_pdf_pages_as_png(monkeypatch):
    from audit_workbench.settings import get_settings

    def fake_render_pdf_pages_png(document_bytes, *, settings, dpi, max_edge=None):
        assert document_bytes == b"%PDF-1.7"
        assert dpi == settings.repody_vlm_pdf_dpi
        assert max_edge == settings.repody_vlm_max_edge_px
        return [b"rendered-page"]

    monkeypatch.setattr(
        "audit_workbench.extraction.preprocess.render_pdf_pages_png",
        fake_render_pdf_pages_png,
    )
    bundle = DocumentBundle(raw_bytes=b"%PDF-1.7", mime_type="application/pdf")

    pages, pages_rendered = _vlm_pages(bundle, get_settings())

    assert pages == [(b"rendered-page", "image/png")]
    assert pages_rendered == 1


def test_repody_vlm_encodes_page_mime_type_in_data_url():
    content = _encode_pages_for_vlm([(b"page", "image/png")])

    assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")


def test_repody_vlm_markdown_payload_uses_nuextract_mode():
    from audit_workbench.catalog.registry import parse_document_model
    from audit_workbench.settings import get_settings

    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    payload = _markdown_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        page_count=2,
        settings=get_settings(),
    )

    assert payload["chat_template_kwargs"]["mode"] == "markdown"
    assert "template" not in payload["chat_template_kwargs"]
    assert payload["max_tokens"] >= 1024


def test_repody_vlm_structured_payload_keeps_template():
    from audit_workbench.catalog.registry import parse_document_model
    from audit_workbench.settings import get_settings

    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    schema = [SchemaFieldSpec(name="invoice_number", description="Invoice number")]
    payload = _structured_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        schema=schema,
        extraction_instructions="Use ISO dates.",
        settings=get_settings(),
    )

    assert "template" in payload["chat_template_kwargs"]
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
    assert payload["temperature"] == 0.2
    assert "top_p" not in payload
    assert payload["chat_template_kwargs"]["instructions"] == "Use ISO dates.\nField instructions:\n- `invoice_number`: Invoice number"


def test_repody_vlm_thinking_payload_matches_nuextract_docs():
    from audit_workbench.catalog.registry import parse_document_model
    from audit_workbench.settings import Settings

    settings = Settings(repody_vlm_enable_thinking=True)
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    schema = [SchemaFieldSpec(name="invoice_number", description="Invoice number")]
    structured = _structured_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        schema=schema,
        extraction_instructions="",
        settings=settings,
    )
    markdown = _markdown_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        page_count=1,
        settings=settings,
    )

    assert structured["temperature"] == 0.6
    assert structured["top_p"] == 0.95
    assert structured["top_k"] == 40
    assert markdown["temperature"] == 0.7
    assert markdown["top_p"] == 0.95
    assert markdown["top_k"] == 40


def test_strip_vlm_thinking_removes_reasoning_wrapper():
    end_tag = "</" + "think" + ">"
    raw = f"long chain{end_tag}\n\n# Invoice"
    assert strip_vlm_thinking(raw) == "# Invoice"


@pytest.mark.asyncio
async def test_pipeline_calls_document_model_catalog(monkeypatch):
    direct_result = ExtractionResult(fields=[])
    extract_mock = AsyncMock(return_value=direct_result)
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.extract_with_document_model",
        extract_mock,
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.get_cached",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.set_cached",
        AsyncMock(),
    )
    from audit_workbench.extraction.pipeline import PipelineExtractor

    bundle = DocumentBundle(
        raw_bytes=b"image",
        mime_type="image/jpeg",
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.load_document_bundle",
        lambda *a, **k: bundle,
    )

    result = await PipelineExtractor().extract(
        b"image",
        "image/jpeg",
        "Invoice",
        [SchemaFieldSpec(name="total_amount", description="Total TTC")],
        extraction_mode="document_model",
        document_model_id=REPODY_VLM_CATALOG_ID,
        validation_mode="logic_only",
    )

    assert result is direct_result
    extract_mock.assert_awaited_once()


def test_repody_vlm_missing_field_is_not_marked_extracted():
    schema = [SchemaFieldSpec(name="missing_value", description="Absent field")]
    wrapped = json.loads(_fields_payload("{}", schema))
    assert wrapped["fields"][0]["value"] == ""
    fields = parse_fields_json(json.dumps(wrapped), schema)
    assert fields[0].extracted is False


def test_parse_document_model_returns_registered_spec():
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.id == REPODY_VLM_CATALOG_ID
    assert spec.runtime == "docker_model_runner"
