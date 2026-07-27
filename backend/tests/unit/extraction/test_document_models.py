from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from audit_workbench.extraction.types import ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.types import DocumentBundle
from audit_workbench.extraction.parse import parse_fields_json
from audit_workbench.extraction.branding import (
    REPODY_VLM_CATALOG_ID,
    UnknownCatalogIdError,
)
from audit_workbench.catalog.registry import (
    normalize_model_id,
    parse_document_model,
)
from audit_workbench.extraction.nuextract import build_vlm_template
from audit_workbench.extraction.render import (
    _encode_pages_for_vlm,
    _vlm_pages,
    cap_vlm_pages,
)
from audit_workbench.extraction.payloads import (
    _fields_payload,
    _markdown_payload,
    _structured_payload,
    build_vlm_instructions,
    strip_vlm_thinking,
)
from audit_workbench.extraction.payloads import build_icl_messages


def test_catalog_routes_repody_vlm_to_llamacpp():
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.runtime == "llamacpp"
    assert spec.engine == "document_model"


def test_catalog_routes_repody_vlm_cloud_when_enabled(monkeypatch):
    from audit_workbench.extraction.branding import REPODY_VLM_CLOUD_CATALOG_ID
    from audit_workbench.settings import get_settings

    monkeypatch.setenv("AUDIT_NUEXTRACT_CLOUD_ENABLED", "true")
    get_settings.cache_clear()
    try:
        import audit_workbench.extraction.vlm  # noqa: F401

        spec = parse_document_model(REPODY_VLM_CLOUD_CATALOG_ID)
        assert spec.runtime == "nuextract_cloud"
        assert spec.id == REPODY_VLM_CLOUD_CATALOG_ID
    finally:
        get_settings.cache_clear()


def test_unknown_model_id_raises():
    with pytest.raises(UnknownCatalogIdError, match="unknown-model"):
        normalize_model_id("unknown-model")


def test_repody_vlm_template_and_flat_json():
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
    assert fields[0].value == "6000.0"
    assert fields[1].value == "FAC-42"


def test_repody_vlm_list_template_and_payload():
    from audit_workbench.extraction.template_types import suggest_template_type

    schema = [
        SchemaFieldSpec(
            name="unit_prices",
            description="list of amounts for each line item",
            template_type="number-list",
        )
    ]

    assert build_vlm_template(schema) == {"unit_prices": ["number"]}
    assert suggest_template_type("amounts", "list of amount per line item") == "number-list"

    wrapped = _fields_payload(
        json.dumps({"unit_prices": [12.5, 3.0, 99.99]}),
        schema,
    )
    fields = parse_fields_json(wrapped, schema)
    assert json.loads(fields[0].value) == [12.5, 3.0, 99.99]


def test_repody_vlm_any_scalar_list_template():
    from audit_workbench.extraction.nuextract import is_list_template_type, normalize_template_type

    schema = [
        SchemaFieldSpec(
            name="beneficiary_ibans",
            description="liste des IBAN bénéficiaires",
            template_type="iban-list",
        ),
        SchemaFieldSpec(
            name="operation_dates",
            description="all operation dates",
            template_type="date-list",
        ),
    ]

    assert normalize_template_type("iban-list") == "iban-list"
    assert is_list_template_type("iban-list")
    assert not is_list_template_type("object-array")

    assert build_vlm_template(schema) == {
        "beneficiary_ibans": ["iban"],
        "operation_dates": ["date"],
    }


def test_repody_vlm_structured_payload_omits_max_tokens_by_default():
    from audit_workbench.catalog.registry import parse_document_model

    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    schema = [
        SchemaFieldSpec(
            name="tags",
            description="all tags",
            template_type="verbatim-string-list",
        )
    ]
    payload = _structured_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        schema=schema,
        extraction_instructions="",
    )
    assert "max_tokens" not in payload


def test_repody_vlm_object_array_template():
    schema = [
        SchemaFieldSpec(
            name="line_items",
            description="One row per line item",
            template_type="object-array",
            children=[
                SchemaFieldSpec(name="description", template_type="verbatim-string"),
                SchemaFieldSpec(name="quantity", template_type="integer"),
                SchemaFieldSpec(name="unit_price", template_type="number"),
            ],
        )
    ]
    assert build_vlm_template(schema) == {
        "line_items": [
            {
                "description": "verbatim-string",
                "quantity": "integer",
                "unit_price": "number",
            }
        ]
    }


def test_repody_vlm_nested_object_template():
    schema = [
        SchemaFieldSpec(
            name="holder_information",
            description="Person block",
            template_type="object",
            children=[
                SchemaFieldSpec(name="full_name", template_type="string"),
                SchemaFieldSpec(name="date_of_birth", template_type="date"),
            ],
        )
    ]
    assert build_vlm_template(schema) == {
        "holder_information": {
            "full_name": "string",
            "date_of_birth": "date",
        }
    }


def test_repody_vlm_empty_object_and_enum_follow_official_constructors():
    from audit_workbench.extraction.nuextract import normalize_template_type

    empty_object = [
        SchemaFieldSpec(name="meta", template_type="object", children=[]),
        SchemaFieldSpec(name="rows", template_type="object-array", children=[]),
        SchemaFieldSpec(name="status", template_type="enum", enum_values=["open", "closed"]),
        SchemaFieldSpec(name="bad_enum", template_type="enum", enum_values=["only"]),
        SchemaFieldSpec(name="tags", template_type="multi-enum", enum_values=["a", "b"]),
    ]
    assert build_vlm_template(empty_object) == {
        "meta": {},
        "rows": [{}],
        "status": ["open", "closed"],
        "bad_enum": "verbatim-string",
        "tags": [["a", "b"]],
    }
    assert normalize_template_type("email") == "email-address"
    assert normalize_template_type("email-list") == "email-address-list"


def test_build_icl_messages_pairs_developer_role():
    from audit_workbench.extraction.types import ExtractionIclExample

    messages = build_icl_messages(
        [
            ExtractionIclExample(
                input="Line 1: Widget x2 @ 12.50",
                output='{"line_items": [{"description": "Widget", "quantity": 2, "unit_price": 12.5}]}',
            )
        ]
    )
    assert len(messages) == 1
    assert messages[0]["role"] == "developer"
    assert messages[0]["content"][0]["text"].startswith("Line 1")


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


def test_pages_dropped_uses_document_page_count():
    from audit_workbench.extraction.render import pages_dropped

    assert pages_dropped(rendered=20, sent=6) == 14
    assert pages_dropped(rendered=3, sent=3) == 0


def test_repody_vlm_rejects_unsupported_mime_type():
    bundle = DocumentBundle(raw_bytes=b"plain text", mime_type="text/plain")

    with pytest.raises(ValueError, match="Unsupported document type"):
        _vlm_pages(bundle)


def test_repody_vlm_preserves_png_upload_bytes():
    bundle = DocumentBundle(raw_bytes=b"\x89PNG\r\n\x1a\nimage-bytes", mime_type="image/png")

    pages, pages_rendered = _vlm_pages(bundle)

    assert pages == [(bundle.raw_bytes, "image/png")]
    assert pages_rendered == 1
    assert bundle.page_count == 1


def test_repody_vlm_renders_pdf_pages_as_png(monkeypatch):
    def fake_render_nuextract_pdf_pages(document_bytes):
        assert document_bytes == b"%PDF-1.7"
        return [b"rendered-page"], 1

    monkeypatch.setattr(
        "audit_workbench.extraction.render.render_nuextract_pdf_pages",
        fake_render_nuextract_pdf_pages,
    )
    bundle = DocumentBundle(raw_bytes=b"%PDF-1.7", mime_type="application/pdf")

    pages, pages_rendered = _vlm_pages(bundle)

    assert pages == [(b"rendered-page", "image/png")]
    assert pages_rendered == 1


def test_repody_vlm_encodes_page_mime_type_in_data_url():
    content = _encode_pages_for_vlm([(b"page", "image/png")])

    assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")


def test_repody_vlm_markdown_payload_uses_nuextract_mode():
    from audit_workbench.catalog.registry import parse_document_model

    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    payload = _markdown_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
    )

    assert payload["chat_template_kwargs"]["mode"] == "markdown"
    assert "template" not in payload["chat_template_kwargs"]
    assert "max_tokens" not in payload
    assert payload["temperature"] == 0.0


def test_repody_vlm_structured_payload_keeps_template():
    from audit_workbench.catalog.registry import parse_document_model

    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    schema = [SchemaFieldSpec(name="invoice_number", description="Invoice number")]
    payload = _structured_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        schema=schema,
        extraction_instructions="Use ISO dates.",
    )

    template = payload["chat_template_kwargs"]["template"]
    assert '"invoice_number": "verbatim-string"' in template
    assert "\n" in template  # NuExtract multimodal examples use indent=4
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
    assert payload["temperature"] == 0.2
    assert "top_p" not in payload
    assert payload["chat_template_kwargs"]["instructions"] == "Use ISO dates.\nField instructions:\n- `invoice_number`: Invoice number"


def test_repody_vlm_payload_uses_official_non_thinking_defaults():
    from audit_workbench.catalog.registry import parse_document_model

    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    schema = [SchemaFieldSpec(name="invoice_number", description="Invoice number")]
    structured = _structured_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        schema=schema,
        extraction_instructions="",
    )
    markdown = _markdown_payload(
        spec=spec,
        content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
    )

    assert structured["temperature"] == 0.2
    assert structured["chat_template_kwargs"]["enable_thinking"] is False
    assert "max_tokens" not in structured
    assert markdown["temperature"] == 0.0
    assert markdown["chat_template_kwargs"]["enable_thinking"] is False


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
    from audit_workbench.extraction.pipeline import extract_document

    bundle = DocumentBundle(
        raw_bytes=b"image",
        mime_type="image/jpeg",
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.load_document_bundle",
        lambda *a, **k: bundle,
    )

    result = await extract_document(
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
    # Official NuExtract missing leaf is null (not an empty string).
    assert wrapped["fields"][0]["value"] is None
    fields = parse_fields_json(json.dumps(wrapped), schema)
    assert fields[0].extracted is False
    assert fields[0].value == "—"


def test_parse_document_model_returns_registered_spec():
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.id == REPODY_VLM_CATALOG_ID
    assert spec.runtime == "llamacpp"
