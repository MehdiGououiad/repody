"""Document read path and validation mode constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from repody.extraction.branding import public_document_model_label
from repody.inference.runtime import is_remote_inference_url
from repody.rules.types import rule_kind
from repody.settings import Settings, get_settings

ValidationMode = Literal["logic_only", "logic_and_llm"]
LOGIC_VALIDATION: ValidationMode = "logic_only"
RUN_VALIDATION_LLM: ValidationMode = "logic_and_llm"

DOCUMENT_MODEL_READ_PATH_ID = "document_model"
DEFAULT_READ_PATH_ID = DOCUMENT_MODEL_READ_PATH_ID

ReadKind = Literal["document_model"]


@dataclass(frozen=True)
class ReadPathSpec:
    id: str
    label: str
    description: str
    read: ReadKind
    show_document_model: bool = True


@dataclass(frozen=True)
class ValidationModeSpec:
    id: ValidationMode
    label: str
    description: str


READ_PATHS: tuple[ReadPathSpec, ...] = (
    ReadPathSpec(
        id=DOCUMENT_MODEL_READ_PATH_ID,
        label="Document model",
        description="Catalog document model (repody:vlm, paddleocr:qwen, glm:qwen) — labels come from the model registry.",
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
    if mode is None or not str(mode).strip():
        return DEFAULT_READ_PATH_ID
    raw = str(mode).strip().lower()
    if raw in _READ_BY_ID:
        return raw
    raise ValueError(f"Unknown read path {mode!r}. Supported: {', '.join(sorted(_READ_BY_ID))}.")


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


def resolve_read_path_for_document(
    extraction_mode: str | None,
) -> tuple[ReadPathSpec, str]:
    spec = parse_read_path(extraction_mode)
    return spec, spec.id


def read_path_label(path_id: str) -> str:
    try:
        normalized = normalize_read_path_id(path_id)
    except ValueError:
        return READ_PATHS[0].label
    for path in READ_PATHS:
        if path.id == normalized:
            return path.label
    return READ_PATHS[0].label


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
    return any(rule_kind(rule) == "llm" for rule in rules or [])


def resolve_run_validation_mode(
    rules: list[dict] | None,
    settings: Settings | None = None,
) -> ValidationMode:
    if run_uses_llm_validation(rules, settings):
        return RUN_VALIDATION_LLM
    return LOGIC_VALIDATION


def _read_doc_value(doc: object, key: str, default: Any = None) -> Any:
    """Read `key` off a Pydantic model or a raw dict; shape varies by call site."""
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


def extraction_is_needed(
    *,
    has_file: bool,
    has_schema_fields: bool,
    markdown_extraction: bool,
) -> bool:
    """Pure predicate: extract when a file exists and schema or markdown is requested."""
    if not has_file:
        return False
    return has_schema_fields or markdown_extraction


def document_needs_extraction(doc: object, *, has_file: bool) -> bool:
    """True when a run should invoke the extraction pipeline for this document."""
    from repody.catalog.registry import is_markdown_only_model

    model_id = _read_doc_value(doc, "document_model_id", None)
    markdown = bool(_read_doc_value(doc, "markdown_extraction", False)) or is_markdown_only_model(
        str(model_id) if model_id else None
    )
    return extraction_is_needed(
        has_file=has_file,
        has_schema_fields=document_has_schema_fields(doc),
        markdown_extraction=markdown,
    )


GPU_COLD_START_THRESHOLD_MS = 15_000


def is_serverless_inference(settings: Settings | None = None) -> bool:
    """True for remote OpenAI-compatible inference, not local llama-server."""
    settings = settings or get_settings()
    if settings.inference_mode.lower() != "llamacpp":
        return False
    return is_remote_inference_url(settings.llamacpp_base_url)


def gpu_cold_start_likely(
    extraction_ms: int,
    *,
    cache_hit: bool = False,
    settings: Settings | None = None,
) -> bool:
    if cache_hit or extraction_ms < GPU_COLD_START_THRESHOLD_MS:
        return False
    return is_serverless_inference(settings)


def plan_extraction_detail(
    doc: Any,
    *,
    has_file: bool,
    run_validation_mode: str,
) -> str:
    if not has_file:
        return "Schema placeholders (no file uploaded)"
    read_spec = parse_read_path(_read_doc_value(doc, "extraction_mode", DEFAULT_READ_PATH_ID))
    document_model_id = _read_doc_value(doc, "document_model_id")
    # Extraction step only — do not mention validation here (separate progress steps).
    _ = run_validation_mode
    parts = [f"Read: {read_spec.label}"]
    if document_model_id and read_spec.show_document_model:
        parts.append(f"Model: {public_document_model_label(document_model_id)}")
    return " · ".join(parts)


def completed_extraction_detail(meta) -> str:
    read_label = getattr(meta, "read_path_label", None) or read_path_label(
        parse_read_path(
            getattr(meta, "read_path_used", None) or getattr(meta, "read_path_config", None)
        ).id
    )
    val_label = getattr(meta, "validation_label", None) or validation_mode_label(
        meta.validation_mode
    )
    parts = [
        f"Engine: {read_label}",
        f"Validation: {val_label}",
    ]
    if meta.document_model_id:
        parts.append(f"Model: {public_document_model_label(meta.document_model_id)}")
    if meta.cache_hit:
        parts.insert(
            0,
            "Same document as a previous run — reusing cached extraction (skipped extraction/LLM)",
        )
    if meta.gpu_cold_start_likely:
        parts.append("Slow extraction may include GPU warm-up (first request after idle)")
    if meta.pages_dropped and meta.pages_rendered:
        parts.append(
            f"Warning: only {meta.pages_sent} of {meta.pages_rendered} page(s) sent to the model"
        )
    parts.append(f"{meta.fields_extracted} field(s) in {meta.extraction_ms}ms")
    return " · ".join(parts)
