from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from audit_workbench.extraction.base import ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.field_json import parse_fields_json
from audit_workbench.extraction.model_registry import (
    REPODY_VLM_CATALOG_ID,
    normalize_model_id,
    parse_document_model,
)
from audit_workbench.extraction.repody_vlm import (
    _fields_payload,
    build_vlm_instructions,
    build_vlm_template,
    cap_vlm_pages,
)


def test_model_registry_routes_repody_vlm_to_docker_model_runner():
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.runtime == "docker_model_runner"
    assert spec.engine == "document_model"


def test_unknown_model_id_falls_back_to_default():
    assert normalize_model_id("unknown-model") == REPODY_VLM_CATALOG_ID


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


@pytest.mark.asyncio
async def test_pipeline_calls_document_model_registry(monkeypatch):
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
        ocr_model=REPODY_VLM_CATALOG_ID,
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
