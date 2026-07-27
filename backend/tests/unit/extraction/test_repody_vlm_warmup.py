from pathlib import Path

from audit_workbench.extraction.warmup import _mime_type_for_path, _resolve_warmup_document
from audit_workbench.settings import Settings


def test_repody_vlm_warmup_defaults_to_disabled(monkeypatch):
    monkeypatch.delenv("AUDIT_REPODY_VLM_WARMUP_ON_START", raising=False)
    settings = Settings(_env_file=None)
    assert settings.repody_vlm_warmup_on_start is False


def test_resolve_warmup_document_defaults_to_facture_fixture():
    settings = Settings(repody_vlm_warmup_document=None)
    path = _resolve_warmup_document(settings)
    assert path.name == "Facture.pdf"
    assert path.is_file()


def test_resolve_warmup_document_honors_relative_override():
    settings = Settings(repody_vlm_warmup_document="e2e/fixtures/documents/Facture.pdf")
    path = _resolve_warmup_document(settings)
    assert path.is_file()


def test_mime_type_for_path():
    assert _mime_type_for_path(Path("invoice.pdf")) == "application/pdf"
    assert _mime_type_for_path(Path("scan.png")) == "image/png"
