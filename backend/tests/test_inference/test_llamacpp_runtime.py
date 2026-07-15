from __future__ import annotations

from audit_workbench.catalog.registry import _registered_models, parse_document_model
from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID
from audit_workbench.settings import Settings, clear_settings_cache, get_settings


def test_registry_uses_llamacpp_when_inference_mode_llamacpp(monkeypatch):
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "llamacpp")
    monkeypatch.setenv("AUDIT_LLAMACPP_SERVED_MODEL", "test/repody-vlm")
    clear_settings_cache()
    settings = get_settings()
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.runtime == "llamacpp"
    assert spec.runtime_model == "test/repody-vlm"
    assert _registered_models(settings)[REPODY_VLM_CATALOG_ID].runtime == "llamacpp"


def test_registry_uses_llamacpp_served_model(monkeypatch):
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "llamacpp")
    monkeypatch.setenv("AUDIT_LLAMACPP_SERVED_MODEL", "test/repody-vlm")
    clear_settings_cache()
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.runtime == "llamacpp"
    assert spec.runtime_model == "test/repody-vlm"


def test_llamacpp_base_url():
    settings = Settings(
        inference_mode="llamacpp",
        llamacpp_base_url="http://127.0.0.1:8081/v1",
    )
    from audit_workbench.inference.runtime import DOCUMENT_RUNTIME, llamacpp_base_url

    assert DOCUMENT_RUNTIME == "llamacpp"
    assert llamacpp_base_url(settings) == "http://127.0.0.1:8081/v1"


def test_top_k_is_sent_as_openai_extra_body():
    from audit_workbench.inference.openai_compat import split_chat_payload

    standard, extra = split_chat_payload(
        {
            "model": "nuextract",
            "messages": [],
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 40,
            "chat_template_kwargs": {"enable_thinking": True},
        }
    )

    assert standard == {
        "model": "nuextract",
        "messages": [],
        "temperature": 0.6,
        "top_p": 0.95,
    }
    assert extra == {
        "top_k": 40,
        "chat_template_kwargs": {"enable_thinking": True},
    }
