"""Unit tests for PP-OCRv6 markdown adapter (HTTP /ocr)."""

from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx

from repody.catalog.registry import is_markdown_only_model, parse_document_model
from repody.extraction.branding import PADDLEOCR_V6_CATALOG_ID, UnknownCatalogIdError
from repody.extraction.paddleocr_v6 import (
    build_ocr_request_payload,
    extract_with_paddleocr_v6,
    markdown_from_ocr_result,
)
from repody.extraction.types import DocumentBundle
from repody.settings import get_settings


def test_markdown_from_ocr_result_joins_lines():
    payload = {
        "errorCode": 0,
        "result": {
            "ocrResults": [
                {"prunedResult": {"rec_texts": ["ROYAUME DU MAROC", "MEHDI"]}},
                {"prunedResult": {"rec_texts": ["GOUOUIAD"]}},
            ]
        },
    }
    assert markdown_from_ocr_result(payload) == "ROYAUME DU MAROC\nMEHDI\n\nGOUOUIAD"


def test_build_ocr_request_payload_matches_official_serving():
    bundle = DocumentBundle(raw_bytes=b"%PDF-1.4", mime_type="application/pdf")
    payload = build_ocr_request_payload(bundle)
    assert payload["fileType"] == 0
    assert payload["visualize"] is False
    assert payload["useDocOrientationClassify"] is True
    assert payload["useDocUnwarping"] is True
    assert payload["useTextlineOrientation"] is True
    assert base64.b64decode(payload["file"]) == bundle.raw_bytes


def test_build_ocr_request_payload_supports_official_fast_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_USE_DOC_ORIENTATION_CLASSIFY", "false")
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_USE_DOC_UNWARPING", "false")
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_USE_TEXTLINE_ORIENTATION", "false")
    get_settings.cache_clear()
    try:
        bundle = DocumentBundle(raw_bytes=b"jpeg", mime_type="image/jpeg")
        payload = build_ocr_request_payload(bundle)
        assert payload["useDocOrientationClassify"] is False
        assert payload["useDocUnwarping"] is False
        assert payload["useTextlineOrientation"] is False
    finally:
        get_settings.cache_clear()


def test_paddleocr_v6_not_in_workflow_catalog(monkeypatch: pytest.MonkeyPatch):
    """Markdown-only OCR is an internal stage — not a selectable catalog model."""
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_ENABLED", "true")
    get_settings.cache_clear()
    try:
        with pytest.raises(UnknownCatalogIdError):
            parse_document_model(PADDLEOCR_V6_CATALOG_ID)
        assert is_markdown_only_model(PADDLEOCR_V6_CATALOG_ID) is False
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_extract_with_paddleocr_v6_http(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_ENABLED", "true")
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_BASE_URL", "http://paddleocr-v6.test:8868")
    get_settings.cache_clear()
    try:
        route = respx.post("http://paddleocr-v6.test:8868/ocr").mock(
            return_value=httpx.Response(
                200,
                json={
                    "errorCode": 0,
                    "errorMsg": "Success",
                    "result": {
                        "ocrResults": [
                            {"prunedResult": {"rec_texts": ["BE899456", "MEHDI", "GOUOUIAD"]}}
                        ]
                    },
                },
            )
        )
        bundle = DocumentBundle(
            raw_bytes=b"\xff\xd8\xfffakejpeg",
            mime_type="image/jpeg",
        )
        result = await extract_with_paddleocr_v6(bundle, [], "CNIE")
        assert route.called
        assert result.markdown_text is not None
        assert "BE899456" in result.markdown_text
        assert result.fields == []
        payload = json.loads(route.calls.last.request.content.decode())
        assert payload["fileType"] == 1
        assert payload["visualize"] is False
        assert base64.b64decode(payload["file"]) == bundle.raw_bytes
    finally:
        get_settings.cache_clear()
