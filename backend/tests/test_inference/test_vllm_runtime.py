from __future__ import annotations

from audit_workbench.extraction.model_registry import (
    REPODY_VLM_CATALOG_ID,
    _registered_models,
    parse_document_model,
)
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
