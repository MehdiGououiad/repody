"""Unit tests for PP-OCRv6 + Qwen structured adapter."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from repody.catalog.registry import is_markdown_only_model, parse_document_model
from repody.extraction.branding import PADDLEOCR_QWEN_CATALOG_ID
from repody.extraction.paddleocr_qwen import extract_with_paddleocr_qwen
from repody.extraction.types import DocumentBundle, SchemaFieldSpec
from repody.settings import get_settings


def test_paddleocr_qwen_registered_when_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_PADDLEOCR_QWEN_ENABLED", "true")
    get_settings.cache_clear()
    try:
        spec = parse_document_model(PADDLEOCR_QWEN_CATALOG_ID)
        assert spec.markdown_only is False
        assert spec.runtime == "paddleocr_qwen"
        assert is_markdown_only_model(PADDLEOCR_QWEN_CATALOG_ID) is False
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_extract_with_paddleocr_qwen(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_PADDLEOCR_QWEN_ENABLED", "true")
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_BASE_URL", "http://paddleocr-v6.test:8868")
    monkeypatch.setenv("AUDIT_QWEN35_BASE_URL", "http://qwen.test:8084/v1")
    monkeypatch.setenv("AUDIT_QWEN35_SERVED_MODEL", "Qwen3.5-4B")
    get_settings.cache_clear()
    try:
        ocr_route = respx.post("http://paddleocr-v6.test:8868/ocr").mock(
            return_value=httpx.Response(
                200,
                json={
                    "errorCode": 0,
                    "result": {
                        "ocrResults": [
                            {"prunedResult": {"rec_texts": ["BE899456", "MEHDI", "GOUOUIAD"]}}
                        ]
                    },
                },
            )
        )
        qwen_route = respx.post("http://qwen.test:8084/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "national_id": "BE899456",
                                        "first_name": "MEHDI",
                                        "last_name": "GOUOUIAD",
                                    }
                                )
                            }
                        }
                    ]
                },
            )
        )
        bundle = DocumentBundle(raw_bytes=b"jpeg", mime_type="image/jpeg")
        schema = [
            SchemaFieldSpec(name="national_id", description="CIN"),
            SchemaFieldSpec(name="first_name", description="Given name"),
            SchemaFieldSpec(name="last_name", description="Family name"),
        ]
        result = await extract_with_paddleocr_qwen(
            bundle,
            schema,
            "CNIE",
            extraction_instructions="Extract identity fields.",
        )
        assert ocr_route.called
        assert qwen_route.called
        assert result.markdown_text is not None
        assert "BE899456" in result.markdown_text
        by_key = {field.key: field.value for field in result.fields}
        assert by_key["national_id"] == "BE899456"
        assert by_key["first_name"] == "MEHDI"
        assert by_key["last_name"] == "GOUOUIAD"
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_extract_with_paddleocr_qwen_nested_schema(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_PADDLEOCR_QWEN_ENABLED", "true")
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_BASE_URL", "http://paddleocr-v6.test:8868")
    monkeypatch.setenv("AUDIT_QWEN35_BASE_URL", "http://qwen.test:8084/v1")
    monkeypatch.setenv("AUDIT_QWEN35_SERVED_MODEL", "Qwen3.5-4B")
    get_settings.cache_clear()
    try:
        respx.post("http://paddleocr-v6.test:8868/ocr").mock(
            return_value=httpx.Response(
                200,
                json={
                    "errorCode": 0,
                    "result": {
                        "ocrResults": [
                            {
                                "prunedResult": {
                                    "rec_texts": [
                                        "N° BE899456",
                                        "Adresse 125 BD ZIRAOUI CASABLANCA",
                                    ]
                                }
                            }
                        ]
                    },
                },
            )
        )
        qwen_route = respx.post("http://qwen.test:8084/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "national_id": "BE899456",
                                        "address": {
                                            "number": "125",
                                            "street": "BD ZIRAOUI",
                                            "city": "CASABLANCA",
                                        },
                                    }
                                )
                            }
                        }
                    ]
                },
            )
        )
        schema = [
            SchemaFieldSpec(name="national_id", description="CIN"),
            SchemaFieldSpec(
                name="address",
                template_type="object",
                children=[
                    SchemaFieldSpec(name="number", description="Street number"),
                    SchemaFieldSpec(name="street", description="Street name"),
                    SchemaFieldSpec(name="city", description="City"),
                ],
            ),
        ]
        result = await extract_with_paddleocr_qwen(
            DocumentBundle(raw_bytes=b"jpeg", mime_type="image/jpeg"),
            schema,
            "CNIE Verso",
        )
        assert qwen_route.called
        request = json.loads(qwen_route.calls.last.request.content.decode())
        prompt = request["messages"][1]["content"]
        assert "address.city" in prompt
        assert "address.street" in prompt
        by_key = {field.key: field.value for field in result.fields}
        assert by_key["national_id"] == "BE899456"
        assert by_key["address.city"] == "CASABLANCA"
        assert by_key["address.street"] == "BD ZIRAOUI"
        assert by_key["address.number"] == "125"
    finally:
        get_settings.cache_clear()
