from __future__ import annotations

from audit_workbench.extraction.document_model_branding import (
    REPODY_VLM_CATALOG_ID,
    SURYA_OCR2_CATALOG_ID,
)
from audit_workbench.services.model_runtime_config import build_model_runtime_config


def test_model_runtime_config_includes_registered_models(monkeypatch):
    monkeypatch.setenv("AUDIT_REPODY_VLM_ENABLED", "true")
    monkeypatch.setenv("AUDIT_SURYA_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_SURYA_INFERENCE_URL", "http://127.0.0.1:8001/v1")

    payload = build_model_runtime_config()
    ids = {profile.model_id for profile in payload.models}
    assert REPODY_VLM_CATALOG_ID in ids
    assert SURYA_OCR2_CATALOG_ID in ids


def test_surya_image_dpi_documented_as_worker_runtime(monkeypatch):
    monkeypatch.setenv("AUDIT_SURYA_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_SURYA_INFERENCE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.setenv("AUDIT_SURYA_IMAGE_DPI", "96")

    payload = build_model_runtime_config()
    surya = next(m for m in payload.models if m.model_id == SURYA_OCR2_CATALOG_ID)
    dpi = next(f for f in surya.fields if f.key == "surya_image_dpi")
    assert dpi.scope == "worker_runtime"
    assert dpi.env_var == "AUDIT_SURYA_IMAGE_DPI"
    assert dpi.value == 96
    assert dpi.restart == "worker"


def test_surya_mode_toggles_in_runtime_config(monkeypatch):
    monkeypatch.setenv("AUDIT_SURYA_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_SURYA_INFERENCE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.setenv("AUDIT_SURYA_LAYOUT_BLOCK_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_SURYA_TABLE_RECOGNITION_ENABLED", "true")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    payload = build_model_runtime_config()
    surya = next(m for m in payload.models if m.model_id == SURYA_OCR2_CATALOG_ID)
    by_key = {field.key: field for field in surya.fields}
    assert by_key["surya_layout_block_ocr_enabled"].value is True
    assert by_key["surya_table_recognition_enabled"].value is True
    assert by_key["surya_layout_block_ocr_enabled"].env_var == "AUDIT_SURYA_LAYOUT_BLOCK_OCR_ENABLED"
    get_settings.cache_clear()


def test_deployment_notes_present():
    payload = build_model_runtime_config()
    kinds = {note.change_kind for note in payload.deployment_notes}
    assert "AUDIT_* platform env (this panel)" in kinds
    assert "Host inference (llama-server)" in kinds
