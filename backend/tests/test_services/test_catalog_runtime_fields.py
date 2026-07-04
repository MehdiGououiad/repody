from __future__ import annotations

from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID
from audit_workbench.catalog.runtime_fields import build_model_runtime_config


def test_model_runtime_config_includes_registered_models(monkeypatch):
    monkeypatch.setenv("AUDIT_REPODY_VLM_ENABLED", "true")

    payload = build_model_runtime_config()
    ids = {profile.model_id for profile in payload.models}
    assert REPODY_VLM_CATALOG_ID in ids


def test_deployment_notes_present():
    payload = build_model_runtime_config()
    kinds = {note.change_kind for note in payload.deployment_notes}
    assert "AUDIT_* platform env (this panel)" in kinds
    assert "Host inference (llama-server)" in kinds
