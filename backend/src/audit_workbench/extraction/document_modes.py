"""Document read path and validation mode constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DEFAULT_READ_PATH_ID = "document_model"
from audit_workbench.settings import Settings, get_settings

ValidationMode = Literal["logic_only", "logic_and_llm"]
LOGIC_VALIDATION: ValidationMode = "logic_only"
RUN_VALIDATION_LLM: ValidationMode = "logic_and_llm"

ReadKind = Literal["document_model"]


@dataclass(frozen=True)
class ReadPathSpec:
    id: str
    label: str
    description: str
    read: ReadKind
    show_document_model: bool = True

    @property
    def show_ocr_model(self) -> bool:
        return self.show_document_model

    @property
    def ocr_engine(self) -> str:
        return self.read


@dataclass(frozen=True)
class ValidationModeSpec:
    id: ValidationMode
    label: str
    description: str


READ_PATHS: tuple[ReadPathSpec, ...] = (
    ReadPathSpec(
        id=DEFAULT_READ_PATH_ID,
        label="Document model",
        description="Structured field extraction with a registered vision/document model.",
        read="document_model",
    ),
)

_READ_BY_ID = {path.id: path for path in READ_PATHS}

VALIDATION_MODE_OPTIONS: tuple[ValidationModeSpec, ...] = (
    ValidationModeSpec(
        id="logic_only",
        label="Logic rules",
        description="Validate extracted fields with deterministic logic expressions.",
    ),
    ValidationModeSpec(
        id="logic_and_llm",
        label="Logic + LLM rules",
        description="Logic rules plus LLM rule validation when enabled in platform settings.",
    ),
)


def normalize_read_path_id(mode: str | None) -> str:
    if not mode:
        return DEFAULT_READ_PATH_ID
    raw = mode.strip().lower()
    if raw in _READ_BY_ID:
        return raw
    return DEFAULT_READ_PATH_ID


def normalize_validation_mode(
    mode: str | None,
    settings: Settings | None = None,
) -> ValidationMode:
    cfg = settings or get_settings()
    raw = (mode or LOGIC_VALIDATION).strip().lower()
    if raw == RUN_VALIDATION_LLM and cfg.llm_validation_enabled:
        return RUN_VALIDATION_LLM
    return LOGIC_VALIDATION


def normalize_document_modes(
    extraction_mode: str | None,
    validation_mode: str | None = None,
    *,
    settings: Settings | None = None,
) -> tuple[str, ValidationMode]:
    read_id = normalize_read_path_id(extraction_mode)
    val_id = normalize_validation_mode(validation_mode, settings)
    return read_id, val_id


def parse_read_path(mode: str | None) -> ReadPathSpec:
    return _READ_BY_ID[normalize_read_path_id(mode)]


def read_path_used_label(path_id: str) -> str:
    return read_path_label(path_id)


def read_path_label(path_id: str) -> str:
    for path in READ_PATHS:
        if path.id == path_id:
            return path.label
    return "Document model"


def validation_mode_label(mode: ValidationMode | str) -> str:
    if mode == RUN_VALIDATION_LLM:
        return "Logic + LLM rules"
    return "Logic rules"


def list_read_paths() -> list[ReadPathSpec]:
    return list(READ_PATHS)


def list_validation_modes(settings: Settings | None = None) -> list[ValidationModeSpec]:
    cfg = settings or get_settings()
    if cfg.llm_validation_enabled:
        return list(VALIDATION_MODE_OPTIONS)
    return [mode for mode in VALIDATION_MODE_OPTIONS if mode.id != RUN_VALIDATION_LLM]


def run_uses_llm_validation(
    rules: list[dict] | None,
    settings: Settings | None = None,
) -> bool:
    cfg = settings or get_settings()
    if not cfg.llm_validation_enabled:
        return False
    return any((rule.get("kind") or "logic").lower() == "llm" for rule in rules or [])


def resolve_run_validation_mode(
    rules: list[dict] | None,
    settings: Settings | None = None,
) -> ValidationMode:
    if run_uses_llm_validation(rules, settings):
        return RUN_VALIDATION_LLM
    return LOGIC_VALIDATION


def _read_doc_value(doc: object, key: str, default: object = None) -> object:
    value = getattr(doc, key, None)
    if value is not None:
        return value
    if isinstance(doc, dict):
        return doc.get(key, default)
    return default


def document_has_schema_fields(doc: object) -> bool:
    schema_fields = _read_doc_value(doc, "schema_fields", None)
    if schema_fields is None and isinstance(doc, dict):
        schema_fields = doc.get("schema") or []
    for field in schema_fields or []:
        raw = _read_doc_value(field, "name", "")
        if str(raw or "").strip():
            return True
    return False


def document_needs_extraction(doc: object, *, has_file: bool) -> bool:
    """True when a run should invoke the extraction pipeline for this document."""
    if not has_file:
        return False
    if document_has_schema_fields(doc):
        return True
    if bool(_read_doc_value(doc, "markdown_extraction", False)):
        return True
    if isinstance(doc, dict) and bool(doc.get("markdownExtraction")):
        return True
    return False
