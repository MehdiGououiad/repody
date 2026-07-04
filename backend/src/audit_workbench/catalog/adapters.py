"""Document model extraction adapters — breaks catalog ↔ extraction import cycles."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from audit_workbench.extraction.base import ExtractionResult

DocumentModelExtractor = Callable[..., Awaitable[ExtractionResult]]

_adapters: dict[str, DocumentModelExtractor] = {}


def register_document_model_adapter(
    catalog_id: str,
    extractor: DocumentModelExtractor,
) -> None:
    _adapters[catalog_id] = extractor


def get_document_model_adapter(catalog_id: str) -> DocumentModelExtractor | None:
    return _adapters.get(catalog_id)
