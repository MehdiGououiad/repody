from __future__ import annotations

import time

import structlog

from audit_workbench.extraction.base import (
    DocumentExtractor,
    ExtractionResult,
    SchemaFieldSpec,
)
from audit_workbench.extraction.document_bundle import DocumentBundle, load_document_bundle
from audit_workbench.extraction.model_registry import (
    extract_with_document_model,
    parse_document_model,
)
from audit_workbench.extraction.schema_fields import empty_fields_from_schema
from audit_workbench.settings import get_settings

log = structlog.get_logger()


class DocumentModelExtractor(DocumentExtractor):
    """Dispatch structured extraction to a registered document model."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def extract(
        self,
        document_bytes: bytes | None,
        mime_type: str,
        document_type: str,
        schema: list[SchemaFieldSpec],
        *,
        extraction_mode: str = "document_model",
        ocr_model: str | None = None,
        storage_key: str | None = None,
        file_size: int | None = None,
        bundle: DocumentBundle | None = None,
        validation_mode: str = "logic_only",
        llm_rules: list[dict] | None = None,
        llm_model: str | None = None,
        allow_combined_llm: bool = True,
    ) -> ExtractionResult:
        _ = (
            storage_key,
            file_size,
            extraction_mode,
            validation_mode,
            llm_rules,
            llm_model,
            allow_combined_llm,
        )
        if not document_bytes or not schema:
            return ExtractionResult(fields=empty_fields_from_schema(schema), raw_text=None)

        spec = parse_document_model(ocr_model)
        started = time.perf_counter()
        doc_bundle = bundle or load_document_bundle(
            document_bytes,
            mime_type,
            settings=self._settings,
        )
        result = await extract_with_document_model(spec, doc_bundle, schema, document_type)
        log.info(
            "document_model_extracted",
            model_id=spec.id,
            runtime=spec.runtime,
            runtime_model=spec.runtime_model,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return result
