"""Unified document model catalog."""

from audit_workbench.catalog.registry import (
    DEFAULT_READ_PATH_ID,
    DocumentEngine,
    DocumentModelSpec,
    DocumentRuntime,
    extract_with_document_model,
    is_markdown_only_model,
    list_document_models,
    normalize_model_id,
    parse_document_model,
)
from audit_workbench.catalog.runtime_fields import build_model_runtime_config

__all__ = [
    "DEFAULT_READ_PATH_ID",
    "DocumentEngine",
    "DocumentModelSpec",
    "DocumentRuntime",
    "build_model_runtime_config",
    "extract_with_document_model",
    "is_markdown_only_model",
    "list_document_models",
    "normalize_model_id",
    "parse_document_model",
]
