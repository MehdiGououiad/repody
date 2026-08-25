"""Unit tests for GLM-OCR + Qwen structured adapter."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from repody.catalog.registry import is_markdown_only_model, parse_document_model
from repody.extraction.branding import GLM_OCR_QWEN_CATALOG_ID
from repody.extraction.glm_ocr_qwen import extract_with_glm_ocr_qwen
from repody.extraction.types import DocumentBundle, SchemaFieldSpec
from repody.settings import get_settings


def test_glm_ocr_qwen_registered_when_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_GLM_OCR_QWEN_ENABLED", "true")
    get_settings.cache_clear()
    try:
        spec = parse_document_model(GLM_OCR_QWEN_CATALOG_ID)
        assert spec.markdown_only is False
        assert spec.runtime == "glm_ocr_qwen"
        assert is_markdown_only_model(GLM_OCR_QWEN_CATALOG_ID) is False
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_extract_with_glm_ocr_qwen(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_GLM_OCR_QWEN_ENABLED", "true")
    monkeypatch.setenv("AUDIT_GLM_OCR_BASE_URL", "http://glm.test:8083/v1")
    monkeypatch.setenv("AUDIT_QWEN35_BASE_URL", "http://qwen.test:8084/v1")
    monkeypatch.setenv("AUDIT_QWEN35_SERVED_MODEL", "Qwen3.5-4B")
    get_settings.cache_clear()

    async def _fake_markdown(bundle):
        _ = bundle
        return "Total TTC 6000.00\nTVA 1000.00", 1, 1, 0

    monkeypatch.setattr(
        "repody.extraction.glm_ocr_qwen.fetch_glm_ocr_markdown",
        _fake_markdown,
    )
    try:
        qwen_route = respx.post("http://qwen.test:8084/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps({"total_amount": "6000.00", "tva": "1000.00"})
                            }
                        }
                    ]
                },
            )
        )
        bundle = DocumentBundle(raw_bytes=b"%PDF-1.4", mime_type="application/pdf")
        schema = [
            SchemaFieldSpec(name="total_amount", description="Total TTC"),
            SchemaFieldSpec(name="tva", description="TVA"),
        ]
        result = await extract_with_glm_ocr_qwen(bundle, schema, "Invoice")
        assert qwen_route.called
        by_key = {field.key: field.value for field in result.fields}
        assert by_key["total_amount"] == "6000.00"
        assert by_key["tva"] == "1000.00"
        assert result.markdown_text is not None
        assert "6000" in result.markdown_text
    finally:
        get_settings.cache_clear()
