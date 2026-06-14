from audit_workbench.extraction.processing_paths import (
    list_read_paths,
    list_validation_modes,
    normalize_document_modes,
    parse_read_path,
    parse_validation_mode,
)
from audit_workbench.services.audit_pipeline import rules_for_validation


def test_document_model_read_path():
    paths = list_read_paths()
    assert len(paths) == 1
    assert paths[0].id == "document_model"
    assert parse_read_path(None).id == "document_model"


def test_logic_only_validation():
    modes = list_validation_modes()
    assert len(modes) == 1
    assert modes[0].id == "logic_only"
    assert parse_validation_mode(None) == "logic_only"


def test_unknown_read_path_normalizes_to_document_model():
    read, val = normalize_document_modes("unknown_legacy_mode", "anything")
    assert read == "document_model"
    assert val == "logic_only"


def test_logic_only_skips_llm_rules():
    rules = [
        {"id": "1", "kind": "logic", "name": "Math"},
        {"id": "2", "kind": "llm", "name": "Fees"},
    ]
    active, skipped = rules_for_validation(rules, "logic_only")
    assert len(active) == 1
    assert len(skipped) == 1
