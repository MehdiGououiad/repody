from pathlib import Path

from repody.extraction.warmup import (
    _mime_type_for_path,
    _resolve_warmup_document,
    _warmup_bundle,
)
from repody.settings import Settings


def test_repody_vlm_warmup_defaults_to_disabled(monkeypatch):
    monkeypatch.delenv("AUDIT_REPODY_VLM_WARMUP_ON_START", raising=False)
    settings = Settings(_env_file=None)
    assert settings.repody_vlm_warmup_on_start is False


def test_resolve_warmup_document_defaults_to_none():
    settings = Settings(repody_vlm_warmup_document=None)
    assert _resolve_warmup_document(settings) is None


def test_warmup_bundle_uses_synthetic_png_when_unset():
    settings = Settings(repody_vlm_warmup_document=None)
    bundle, label = _warmup_bundle(settings)
    assert bundle is not None
    assert bundle.mime_type == "image/png"
    assert label == "synthetic:1x1.png"


def test_resolve_warmup_document_honors_relative_override():
    settings = Settings(repody_vlm_warmup_document="e2e/fixtures/documents/Facture.pdf")
    path = _resolve_warmup_document(settings)
    assert path is not None
    assert path.is_file()


def test_mime_type_for_path():
    assert _mime_type_for_path(Path("document.pdf")) == "application/pdf"
    assert _mime_type_for_path(Path("scan.png")) == "image/png"
