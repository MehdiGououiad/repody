from __future__ import annotations

from audit_workbench.inference.runtime import effective_parallel_doc_extraction
from audit_workbench.settings import Settings, clear_settings_cache, get_settings


def test_auto_parallel_off_for_docker_model_runner(monkeypatch):
    monkeypatch.delenv("AUDIT_PARALLEL_DOC_EXTRACTION", raising=False)
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "docker_model_runner")
    clear_settings_cache()
    assert effective_parallel_doc_extraction(get_settings()) is False


def test_auto_parallel_on_for_vllm(monkeypatch):
    monkeypatch.delenv("AUDIT_PARALLEL_DOC_EXTRACTION", raising=False)
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "vllm")
    clear_settings_cache()
    assert effective_parallel_doc_extraction(get_settings()) is True


def test_explicit_parallel_true_on_model_runner(monkeypatch):
    monkeypatch.setenv("AUDIT_PARALLEL_DOC_EXTRACTION", "true")
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "docker_model_runner")
    clear_settings_cache()
    assert effective_parallel_doc_extraction(get_settings()) is True


def test_explicit_parallel_false_on_vllm(monkeypatch):
    monkeypatch.setenv("AUDIT_PARALLEL_DOC_EXTRACTION", "false")
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "vllm")
    clear_settings_cache()
    assert effective_parallel_doc_extraction(get_settings()) is False


def test_settings_field_none_by_default(monkeypatch):
    monkeypatch.delenv("AUDIT_PARALLEL_DOC_EXTRACTION", raising=False)
    clear_settings_cache()
    assert Settings().parallel_doc_extraction is None
