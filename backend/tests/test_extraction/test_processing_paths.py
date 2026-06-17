from audit_workbench.extraction.document_modes import (
    LOGIC_VALIDATION,
    RUN_VALIDATION_LLM,
    list_read_paths,
    list_validation_modes,
    normalize_document_modes,
    parse_read_path,
    resolve_run_validation_mode,
)
from audit_workbench.rules.runner import rules_for_validation


def test_document_model_read_path():
    paths = list_read_paths()
    ids = {path.id for path in paths}
    assert "document_model" in ids
    assert len(paths) >= 1
    assert parse_read_path(None).id == "document_model"


def test_legacy_read_path_aliases_normalize_to_document_model():
    paths = list_read_paths()
    ids = {path.id for path in paths}
    assert ids == {"document_model"}
    assert parse_read_path("paddle").id == "document_model"
    assert parse_read_path("paddle_ocr").id == "document_model"


def test_validation_mode_catalog():
    modes = list_validation_modes()
    ids = {mode.id for mode in modes}
    assert ids == {LOGIC_VALIDATION, RUN_VALIDATION_LLM}


def test_unknown_read_path_normalizes_to_document_model():
    read, val = normalize_document_modes("unknown_legacy_mode", "anything")
    assert read == "document_model"
    assert val == LOGIC_VALIDATION


def test_logic_only_skips_llm_rules():
    rules = [
        {"id": "1", "kind": "logic", "name": "Math"},
        {"id": "2", "kind": "llm", "name": "Fees"},
    ]
    active, skipped = rules_for_validation(rules, LOGIC_VALIDATION)
    assert len(active) == 1
    assert len(skipped) == 1


def test_resolve_run_validation_mode_with_llm_rules(monkeypatch):
    monkeypatch.setenv("AUDIT_LLM_VALIDATION_ENABLED", "true")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    rules = [{"id": "1", "kind": "llm", "name": "Check"}]
    assert resolve_run_validation_mode(rules) == RUN_VALIDATION_LLM
    get_settings.cache_clear()
