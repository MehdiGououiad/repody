from __future__ import annotations

from audit_workbench.catalog.registry import _registered_models
from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID
from audit_workbench.catalog.registry import parse_document_model
from audit_workbench.settings import Settings, clear_settings_cache, get_settings


def test_registry_uses_vllm_when_inference_mode_vllm(monkeypatch):
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "vllm")
    monkeypatch.setenv("AUDIT_VLLM_SERVED_MODEL", "test/repody-vlm")
    clear_settings_cache()
    settings = get_settings()
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.runtime == "vllm"
    assert spec.runtime_model == "test/repody-vlm"
    assert _registered_models(settings)[REPODY_VLM_CATALOG_ID].runtime == "vllm"


def test_registry_uses_model_runner_on_cpu(monkeypatch):
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "docker_model_runner")
    monkeypatch.setenv("AUDIT_REPODY_VLM_MODEL", "repody/repody-vlm:q4_k_m-16k")
    clear_settings_cache()
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    assert spec.runtime == "docker_model_runner"
    assert spec.runtime_model == "repody/repody-vlm:q4_k_m-16k"


def test_openai_base_url_for_vllm():
    settings = Settings(inference_mode="vllm", vllm_base_url="http://vllm:8000/v1")
    from audit_workbench.inference.runtime import openai_base_url_for_runtime

    assert openai_base_url_for_runtime("vllm", settings) == "http://vllm:8000/v1"


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
