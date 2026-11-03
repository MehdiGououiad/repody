import pytest

from repody.extraction.modes import (
    DOCUMENT_MODEL_READ_PATH_ID,
    LOGIC_VALIDATION,
    list_read_paths,
    list_validation_modes,
    normalize_document_modes,
    normalize_read_path_id,
    parse_read_path,
)


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


def test_retired_llm_validation_mode_resolves_to_logic():
    read, val = normalize_document_modes("document_model", "logic_and_llm")
    assert read == DOCUMENT_MODEL_READ_PATH_ID
    assert val == LOGIC_VALIDATION


def test_validation_mode_catalog_default_logic_only():
    modes = list_validation_modes()
    ids = {mode.id for mode in modes}
    assert ids == {LOGIC_VALIDATION}


async def test_legacy_llm_rules_are_reported_as_skipped():
    from repody.rules.runner import evaluate_rules

    results = await evaluate_rules(
        [{"id": "r1", "name": "Old LLM rule", "kind": "llm", "body": "is this fine?"}], {}
    )
    assert [(r.id, r.status) for r in results] == [("r1", "skipped")]
