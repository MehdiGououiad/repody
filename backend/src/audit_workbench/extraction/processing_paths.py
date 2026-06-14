"""Processing path constants — Repody VLM document model + logic-only validation.

The platform currently ships a single read path and validation mode. API parameters
are accepted for forward compatibility but normalize to these defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from audit_workbench.extraction.model_registry import DEFAULT_READ_PATH_ID

ReadKind = Literal["document_model"]
ValidationKind = Literal["logic_only"]


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
        return "document_model"


@dataclass(frozen=True)
class ValidationModeSpec:
    id: ValidationKind
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

VALIDATION_MODES: tuple[ValidationModeSpec, ...] = (
    ValidationModeSpec(
        id="logic_only",
        label="Logic rules",
        description="Validate extracted fields with deterministic logic expressions.",
    ),
)

_READ_BY_ID = {path.id: path for path in READ_PATHS}


def normalize_read_path_id(mode: str | None) -> str:
    if not mode:
        return DEFAULT_READ_PATH_ID
    raw = mode.strip().lower()
    if raw in _READ_BY_ID:
        return raw
    return DEFAULT_READ_PATH_ID


def normalize_document_modes(
    extraction_mode: str | None,
    validation_mode: str | None = None,
) -> tuple[str, ValidationKind]:
    _ = validation_mode
    return normalize_read_path_id(extraction_mode), "logic_only"


def parse_read_path(mode: str | None) -> ReadPathSpec:
    return _READ_BY_ID[normalize_read_path_id(mode)]


def parse_validation_mode(
    validation_mode: str | None,
    *,
    extraction_mode: str | None = None,
) -> ValidationKind:
    _ = validation_mode, extraction_mode
    return "logic_only"


def list_read_paths() -> list[ReadPathSpec]:
    return list(READ_PATHS)


def list_validation_modes() -> list[ValidationModeSpec]:
    return list(VALIDATION_MODES)


def resolve_run_validation(
    validation_modes: list[ValidationKind],
) -> ValidationKind:
    _ = validation_modes
    return "logic_only"


def validation_mode_label(mode: ValidationKind | str) -> str:
    _ = mode
    return "Logic rules"


def read_path_used_label(path_id: str) -> str:
    spec = _READ_BY_ID.get(path_id)
    return spec.label if spec else "Document model"
