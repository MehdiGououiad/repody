import pytest

from audit_workbench.extraction.document_modes import (
    DOCUMENT_MODEL_READ_PATH_ID,
    LOGIC_VALIDATION,
    RUN_VALIDATION_LLM,
    list_read_paths,
    list_validation_modes,
    normalize_document_modes,
    normalize_read_path_id,
    parse_read_path,
)
from audit_workbench.rules.runner import rules_for_validation


def test_read_path_catalog():
    paths = list_read_paths()
    ids = {path.id for path in paths}
    assert ids == {DOCUMENT_MODEL_READ_PATH_ID}
    assert parse_read_path(None).id == DOCUMENT_MODEL_READ_PATH_ID


def test_empty_read_path_defaults_to_document_model():
    assert normalize_read_path_id(None) == DOCUMENT_MODEL_READ_PATH_ID
    assert normalize_read_path_id("") == DOCUMENT_MODEL_READ_PATH_ID
    assert normalize_read_path_id("  ") == DOCUMENT_MODEL_READ_PATH_ID


def test_unknown_read_path_raises():
    with pytest.raises(ValueError, match="Unknown read path"):
        normalize_document_modes("pdf_text", "logic_only")
    with pytest.raises(ValueError, match="Unknown read path"):
        normalize_document_modes("auto", "logic_only")
    with pytest.raises(ValueError, match="Unknown read path"):
        normalize_document_modes("unknown_mode", "anything")


def test_normalize_document_modes_honors_validation_mode(monkeypatch):
    monkeypatch.setenv("AUDIT_LLM_VALIDATION_ENABLED", "true")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    read, val = normalize_document_modes("document_model", "logic_and_llm")
    assert read == DOCUMENT_MODEL_READ_PATH_ID
    assert val == RUN_VALIDATION_LLM
    get_settings.cache_clear()


def test_normalize_document_modes_downgrades_llm_when_disabled():
    read, val = normalize_document_modes("document_model", "logic_and_llm")
    assert read == DOCUMENT_MODEL_READ_PATH_ID
    assert val == LOGIC_VALIDATION


def test_validation_mode_catalog_default_logic_only():
    modes = list_validation_modes()
    ids = {mode.id for mode in modes}
    assert ids == {LOGIC_VALIDATION}


def test_logic_only_skips_llm_rules():
    rules = [
        {"id": "1", "kind": "logic", "name": "Math"},
        {"id": "2", "kind": "llm", "name": "Fees"},
    ]
    active, skipped = rules_for_validation(rules, LOGIC_VALIDATION)
    assert len(active) == 1
    assert len(skipped) == 1
