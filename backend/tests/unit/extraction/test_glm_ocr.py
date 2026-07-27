"""Unit tests for GLM-OCR markdown adapter (chat/completions + official OCR prompt)."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from audit_workbench.catalog.registry import is_markdown_only_model, parse_document_model
from audit_workbench.extraction.branding import GLM_OCR_CATALOG_ID
from audit_workbench.extraction.glm_ocr import extract_with_glm_ocr
from audit_workbench.extraction.ocr_chat import (
    build_ocr_user_content,
    markdown_from_chat_response,
)
from audit_workbench.extraction.render import GLM_OCR_TEXT_PROMPT
from audit_workbench.extraction.types import DocumentBundle
from audit_workbench.settings import get_settings


def test_markdown_from_chat_response():
    payload = {
        "choices": [
            {"message": {"role": "assistant", "content": "  ROYAUME DU MAROC\nMEHDI  "}}
        ]
    }
    assert markdown_from_chat_response(payload) == "ROYAUME DU MAROC\nMEHDI"


def test_build_ocr_user_content_image_then_ocr_prompt():
    content = build_ocr_user_content(b"\x89PNG\r\n\x1a\n", text_prompt=GLM_OCR_TEXT_PROMPT)
    assert len(content) == 2
    assert content[0]["type"] == "image_url"
    assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert content[1] == {"type": "text", "text": "Text Recognition:"}


def test_glm_ocr_registered_when_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_GLM_OCR_ENABLED", "true")
    get_settings.cache_clear()
    try:
        spec = parse_document_model(GLM_OCR_CATALOG_ID)
        assert spec.markdown_only is True
        assert spec.runtime_model == "GLM-OCR"
        assert is_markdown_only_model(GLM_OCR_CATALOG_ID) is True
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_extract_with_glm_ocr_http(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_GLM_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_GLM_OCR_BASE_URL", "http://glm.test:8083/v1")
    monkeypatch.setenv("AUDIT_GLM_OCR_SERVED_MODEL", "GLM-OCR")
    get_settings.cache_clear()

    captured: dict[str, Any] = {}

    async def _fake_chat(
        base_url: str,
        payload: dict[str, Any],
        *,
        timeout: float,
        api_key: str | None = None,
    ):
        _ = timeout
        _ = api_key
        captured["base_url"] = base_url
        captured["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "BE899456\nMEHDI\nGOUOUIAD",
                    }
                }
            ]
        }

    monkeypatch.setattr(
        "audit_workbench.extraction.ocr_chat.post_chat_completion",
        _fake_chat,
    )
    try:
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        bundle = DocumentBundle(raw_bytes=png, mime_type="image/png")
        result = await extract_with_glm_ocr(bundle, [], "CNIE")
        assert captured["base_url"] == "http://glm.test:8083/v1"
        messages = captured["payload"]["messages"]
        assert len(messages) == 1
        content = messages[0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "image_url"
        assert content[1] == {"type": "text", "text": "Text Recognition:"}
        assert captured["payload"]["temperature"] == 0.0
        assert captured["payload"]["top_k"] == 1
        assert captured["payload"]["top_p"] == 0.00001
        assert captured["payload"]["repeat_penalty"] == 1.1
        assert captured["payload"]["max_tokens"] == 8192
        assert result.markdown_text is not None
        assert "BE899456" in result.markdown_text
        assert result.fields == []
        assert result.pages_sent == 1
    finally:
        get_settings.cache_clear()
