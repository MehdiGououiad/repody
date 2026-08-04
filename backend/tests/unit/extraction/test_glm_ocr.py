"""Unit tests for GLM-OCR official SDK adapter."""

from __future__ import annotations

import base64
from typing import Any
from unittest.mock import MagicMock

import pytest

from repody.catalog.registry import is_markdown_only_model, parse_document_model
from repody.extraction.branding import GLM_OCR_CATALOG_ID
from repody.extraction.glm_ocr import extract_with_glm_ocr
from repody.extraction.glm_ocr_sdk import (
    GlmOcrSdkSettings,
    openai_host_port,
    reset_glm_ocr_sdk_client,
)
from repody.extraction.types import DocumentBundle
from repody.settings import get_settings


def test_openai_host_port_from_v1_base():
    assert openai_host_port("http://127.0.0.1:8083/v1") == ("127.0.0.1", 8083)
    assert openai_host_port("http://host.docker.internal:8083/v1") == (
        "host.docker.internal",
        8083,
    )
    assert openai_host_port("http://127.0.0.1:11434") == ("127.0.0.1", 11434)


def test_glm_ocr_registered_when_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_GLM_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_GLM_OCR_SERVED_MODEL", "GLM-OCR")
    get_settings.cache_clear()
    try:
        spec = parse_document_model(GLM_OCR_CATALOG_ID)
        assert spec.markdown_only is True
        assert spec.runtime_model == "GLM-OCR"
        assert is_markdown_only_model(GLM_OCR_CATALOG_ID) is True
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_extract_requires_sdk_package(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_GLM_OCR_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "repody.extraction.glm_ocr.sdk_importable",
        lambda: False,
    )
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    try:
        with pytest.raises(RuntimeError, match="official glmocr SDK"):
            await extract_with_glm_ocr(
                DocumentBundle(raw_bytes=png, mime_type="image/png"),
                [],
                "CNIE",
            )
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_extract_with_glm_ocr_sdk(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUDIT_GLM_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_GLM_OCR_BASE_URL", "http://127.0.0.1:8083/v1")
    monkeypatch.setenv("AUDIT_GLM_OCR_SERVED_MODEL", "GLM-OCR")
    monkeypatch.setenv("AUDIT_GLM_OCR_LAYOUT_DEVICE", "cpu")
    get_settings.cache_clear()
    reset_glm_ocr_sdk_client()

    monkeypatch.setattr(
        "repody.extraction.glm_ocr.sdk_importable",
        lambda: True,
    )

    def _fake_parse_markdown(document_bytes: bytes, *, cfg: GlmOcrSdkSettings) -> str:
        assert document_bytes
        assert cfg.model == "GLM-OCR"
        assert cfg.layout_device == "cpu"
        assert openai_host_port(cfg.base_url) == ("127.0.0.1", 8083)
        return "# Devis\n\n| Libelle | Montant |\n|---|---|\n| Total | 497550 |"

    monkeypatch.setattr(
        "repody.extraction.glm_ocr.parse_markdown",
        _fake_parse_markdown,
    )
    try:
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        bundle = DocumentBundle(raw_bytes=png, mime_type="image/png")
        result = await extract_with_glm_ocr(bundle, [], "DEVIS")
        assert result.markdown_text is not None
        assert "497550" in result.markdown_text
        assert result.fields == []
    finally:
        reset_glm_ocr_sdk_client()
        get_settings.cache_clear()


def test_sdk_parse_markdown(monkeypatch: pytest.MonkeyPatch):
    """SDK parse_markdown returns markdown_result from official GlmOcr.parse."""
    reset_glm_ocr_sdk_client()
    import repody.extraction.glm_ocr_sdk as sdk_mod

    class _FakeParser:
        def parse(self, data: bytes, *, save_layout_visualization: bool = True):
            assert data == b"%PDF"
            assert save_layout_visualization is False
            out = MagicMock()
            out.markdown_result = "layout+ocr ok"
            return out

        def close(self) -> None:
            return None

    monkeypatch.setattr(sdk_mod, "_build_parser", lambda cfg: _FakeParser())
    md = sdk_mod.parse_markdown(
        b"%PDF",
        cfg=GlmOcrSdkSettings(
            base_url="http://127.0.0.1:8083/v1",
            model="GLM-OCR",
            timeout_seconds=180,
            layout_device="cpu",
            layout_model_dir="PaddlePaddle/PP-DocLayoutV3_safetensors",
            max_workers=4,
            pdf_max_pages=None,
        ),
    )
    assert md == "layout+ocr ok"
    reset_glm_ocr_sdk_client()


def test_build_parser_uses_official_selfhosted_api(monkeypatch: pytest.MonkeyPatch):
    """Constructor matches HF docs: GlmOcr(mode='selfhosted', …)."""
    captured: dict[str, Any] = {}

    class _FakeGlmOcr:
        def __init__(self, **kwargs: Any):
            captured.update(kwargs)

        def close(self) -> None:
            return None

    fake_mod = MagicMock()
    fake_mod.GlmOcr = _FakeGlmOcr
    monkeypatch.setitem(__import__("sys").modules, "glmocr", fake_mod)

    import repody.extraction.glm_ocr_sdk as sdk_mod

    parser = sdk_mod._build_parser(
        GlmOcrSdkSettings(
            base_url="http://127.0.0.1:8083/v1",
            model="GLM-OCR",
            timeout_seconds=180,
            layout_device="cpu",
            layout_model_dir="PaddlePaddle/PP-DocLayoutV3_safetensors",
            max_workers=4,
            pdf_max_pages=None,
        )
    )
    assert isinstance(parser, _FakeGlmOcr)
    assert captured["mode"] == "selfhosted"
    assert captured["ocr_api_host"] == "127.0.0.1"
    assert captured["ocr_api_port"] == 8083
    assert captured["model"] == "GLM-OCR"
    assert captured["layout_device"] == "cpu"
    assert "config_path" in captured
    dotted = captured["_dotted"]
    assert dotted["pipeline.layout.model_dir"].endswith("PP-DocLayoutV3_safetensors")
    assert "pipeline.page_loader.pdf_max_pages" not in dotted
    assert dotted["pipeline.ocr_api.api_port"] == 8083
    assert dotted["pipeline.ocr_api.api_mode"] == "openai"
    assert dotted["pipeline.ocr_api.api_path"] == "/v1/chat/completions"


def test_build_parser_id_card_profile_uses_idcard_config(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    class _FakeGlmOcr:
        def __init__(self, **kwargs: Any):
            captured.update(kwargs)

        def close(self) -> None:
            return None

    fake_mod = MagicMock()
    fake_mod.GlmOcr = _FakeGlmOcr
    monkeypatch.setitem(__import__("sys").modules, "glmocr", fake_mod)

    import repody.extraction.glm_ocr_sdk as sdk_mod

    sdk_mod._build_parser(
        GlmOcrSdkSettings(
            base_url="http://127.0.0.1:8083/v1",
            model="GLM-OCR",
            timeout_seconds=180,
            layout_device="cpu",
            layout_model_dir="PaddlePaddle/PP-DocLayoutV3_safetensors",
            max_workers=4,
            pdf_max_pages=None,
            id_card_profile=True,
        )
    )
    assert captured["config_path"].endswith("config.idcard.yaml")


def test_markdown_from_result_official_no_fallback():
    import repody.extraction.glm_ocr_sdk as sdk_mod

    result = MagicMock()
    result.markdown_result = "![Image 1](x)\n"
    result.json_result = [{"content": "CNIE 123"}]
    assert sdk_mod._markdown_from_result(result, region_text_fallback=False) == "![Image 1](x)"


def test_markdown_from_result_id_card_fallback():
    import repody.extraction.glm_ocr_sdk as sdk_mod

    result = MagicMock()
    result.markdown_result = "![Image 1](x)\n"
    result.json_result = [{"content": "CNIE 123"}]
    assert sdk_mod._markdown_from_result(result, region_text_fallback=True) == "CNIE 123"


def test_build_parser_honors_optional_pdf_max_pages(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    class _FakeGlmOcr:
        def __init__(self, **kwargs: Any):
            captured.update(kwargs)

        def close(self) -> None:
            return None

    fake_mod = MagicMock()
    fake_mod.GlmOcr = _FakeGlmOcr
    monkeypatch.setitem(__import__("sys").modules, "glmocr", fake_mod)

    import repody.extraction.glm_ocr_sdk as sdk_mod

    sdk_mod._build_parser(
        GlmOcrSdkSettings(
            base_url="http://127.0.0.1:8083/v1",
            model="GLM-OCR",
            timeout_seconds=180,
            layout_device="cpu",
            layout_model_dir="PaddlePaddle/PP-DocLayoutV3_safetensors",
            max_workers=4,
            pdf_max_pages=32,
        )
    )
    assert captured["_dotted"]["pipeline.page_loader.pdf_max_pages"] == 32
