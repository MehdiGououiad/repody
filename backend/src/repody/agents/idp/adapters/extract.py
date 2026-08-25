"""VLM extraction adapter — thin function over extract_document."""

from __future__ import annotations

from types import SimpleNamespace

from repody.agents.idp.adapters.mapping import document_extraction_from_result
from repody.agents.idp.contracts import (
    DocumentExtraction,
    DocumentSpec,
    StoredDocument,
)
from repody.app.run.helpers import resolve_run_doc_mime
from repody.extraction.modes import DEFAULT_READ_PATH_ID
from repody.extraction.nuextract import normalize_template_type
from repody.extraction.pipeline import get_extract_document
from repody.extraction.types import ExtractionIclExample, schema_specs_from_fields
from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.settings import get_settings


async def extract_one(
    spec: DocumentSpec,
    stored: StoredDocument,
    raw_bytes: bytes,
    *,
    validation_mode: str = "logic_only",
    icl_examples: list[ExtractionIclExample] | None = None,
) -> Result[DocumentExtraction]:
    """Call the document extractor; return frozen DocumentExtraction."""
    try:
        mime = resolve_run_doc_mime(
            SimpleNamespace(mime_type=stored.mime_type),
            raw_bytes if raw_bytes else None,
        )
        extract_document = get_extract_document()
        extracted = await extract_document(
            raw_bytes or None,
            mime,
            spec.label,
            schema_specs_from_fields(
                spec.schema_fields,
                normalize_template_type=normalize_template_type,
            ),
            extraction_mode=spec.extraction_mode or DEFAULT_READ_PATH_ID,
            document_model_id=spec.document_model_id or get_settings().default_document_model_id,
            storage_key=stored.storage_key,
            file_size=len(raw_bytes) if raw_bytes else None,
            validation_mode=validation_mode,
            extraction_instructions=spec.extraction_instructions,
            markdown_extraction=spec.markdown_extraction,
            native_pdf_auto=spec.native_pdf_auto,
            extraction_icl_examples=icl_examples or None,
        )
        return Result.ok(
            document_extraction_from_result(
                document_id=spec.id,
                result=extracted,
                model_id=spec.document_model_id or "repody:vlm",
            )
        )
    except Exception as exc:
        return Result.fail(
            AppError(
                code=ErrorCode.EXTRACTION,
                message="Document extraction failed",
                document_id=spec.id,
                cause=repr(exc),
            )
        )
