"""Extraction job construction and execution for audit runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from audit_workbench.db.models import Document, RunDocument
from audit_workbench.extraction.base import ExtractionIclExample, ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.schema_spec import icl_examples_from_document
from audit_workbench.extraction.document_modes import DEFAULT_READ_PATH_ID
from audit_workbench.extraction.pipeline import get_extractor
from audit_workbench.services.run.helpers import resolve_run_doc_mime
from audit_workbench.settings import get_settings

PendingFetch = tuple[Document, list[SchemaFieldSpec], RunDocument, int, bool, str]


@dataclass
class DocExtractionJob:
    doc: Document
    schema: list[SchemaFieldSpec]
    run_doc: RunDocument
    document_bytes: bytes | None
    mime_type: str
    file_size: int
    step_index: int
    progress_mode: str
    validation_mode: str
    extraction_instructions: str = ""
    markdown_extraction: bool = False
    extraction_icl_examples: list[ExtractionIclExample] | None = None


async def run_extraction_job(job: DocExtractionJob) -> tuple[DocExtractionJob, ExtractionResult]:
    extractor = get_extractor()
    doc = job.doc
    result = await extractor.extract(
        job.document_bytes,
        job.mime_type,
        doc.document_type,
        job.schema,
        extraction_mode=doc.extraction_mode or DEFAULT_READ_PATH_ID,
        document_model_id=doc.document_model_id or get_settings().default_document_model_id,
        storage_key=job.run_doc.storage_key,
        file_size=job.file_size if job.file_size > 0 else None,
        validation_mode=job.validation_mode,
        extraction_instructions=job.extraction_instructions,
        markdown_extraction=job.markdown_extraction,
        extraction_icl_examples=job.extraction_icl_examples,
    )
    return job, result


async def _fetch_doc_bytes(storage: Any, storage_key: str | None) -> tuple[bytes | None, int]:
    if not storage_key:
        return None, 0
    data = await storage.get_bytes(storage_key)
    return data, len(data)


def _make_extraction_job(
    *,
    doc: Document,
    schema: list[SchemaFieldSpec],
    run_doc: RunDocument,
    document_bytes: bytes | None,
    file_size: int,
    step_index: int,
    prog_mode: str,
    validation_mode: str,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> DocExtractionJob:
    return DocExtractionJob(
        doc=doc,
        schema=schema,
        run_doc=run_doc,
        document_bytes=document_bytes,
        mime_type=resolve_run_doc_mime(run_doc, document_bytes),
        file_size=file_size,
        step_index=step_index,
        progress_mode=prog_mode,
        validation_mode=validation_mode,
        extraction_instructions=extraction_instructions,
        markdown_extraction=markdown_extraction,
        extraction_icl_examples=extraction_icl_examples,
    )


async def build_extraction_jobs(
    storage: Any,
    pending: list[PendingFetch],
    *,
    validation_mode: str,
) -> list[DocExtractionJob]:
    jobs: list[DocExtractionJob] = []
    for doc, schema, run_doc, step_index, _has_file, prog_mode in pending:
        document_bytes, file_size = await _fetch_doc_bytes(storage, run_doc.storage_key)
        jobs.append(
            _make_extraction_job(
                doc=doc,
                schema=schema,
                run_doc=run_doc,
                document_bytes=document_bytes,
                file_size=file_size,
                step_index=step_index,
                prog_mode=prog_mode,
                validation_mode=validation_mode,
                extraction_instructions=getattr(doc, "extraction_instructions", None) or "",
                markdown_extraction=bool(getattr(doc, "markdown_extraction", False)),
                extraction_icl_examples=icl_examples_from_document(doc),
            )
        )
    return jobs
