"""Document extraction phase for audit runs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Document, ExtractedField, RunDocument
from audit_workbench.extraction.base import ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.document_modes import (
    parse_read_path,
    read_path_used_label,
    resolve_run_validation_mode,
    validation_mode_label,
)
from audit_workbench.extraction.gpu_cold_start import is_serverless_vllm
from audit_workbench.extraction.pipeline import get_extractor
from audit_workbench.inference.runtime import effective_parallel_doc_extraction
from audit_workbench.services.run.helpers import (
    extract_label,
    extraction_step_detail,
    meta_to_dict,
    new_id,
    progress_mode,
    resolve_run_doc_mime,
)
from audit_workbench.services.run.phase_state import RunPhaseState
from audit_workbench.services.run_progress import mark_step_done, set_run_progress
from audit_workbench.settings import get_settings
from audit_workbench.storage.factory import get_storage

log = structlog.get_logger()

_GPU_COLD_START_DETAIL = "Serverless GPU may need 1–2 min to start on the first request after idle"


def _annotate_cold_start_hint(steps: list, step_id: str) -> None:
    if not is_serverless_vllm():
        return
    for step in steps:
        if step.get("id") == step_id:
            step["gpuColdStartHint"] = True
            break


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


async def _run_extraction(job: DocExtractionJob) -> tuple[DocExtractionJob, ExtractionResult]:
    extractor = get_extractor()
    doc = job.doc
    result = await extractor.extract(
        job.document_bytes,
        job.mime_type,
        doc.document_type,
        job.schema,
        extraction_mode=doc.extraction_mode or "auto",
        ocr_model=doc.ocr_model or get_settings().default_ocr_model,
        storage_key=job.run_doc.storage_key,
        file_size=job.file_size if job.file_size > 0 else None,
        validation_mode=job.validation_mode,
        extraction_instructions=job.extraction_instructions,
    )
    return job, result


async def _fetch_doc_bytes(storage, storage_key: str | None) -> tuple[bytes | None, int]:
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
    )


async def _build_extraction_jobs(
    storage,
    pending: list[PendingFetch],
    *,
    parallel: bool,
    parallel_fetch: bool,
    validation_mode: str,
) -> list[DocExtractionJob]:
    if parallel:
        if parallel_fetch:
            fetched = await asyncio.gather(
                *[_fetch_doc_bytes(storage, item[2].storage_key) for item in pending]
            )
        else:
            fetched = [await _fetch_doc_bytes(storage, item[2].storage_key) for item in pending]
        return [
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
            )
            for (doc, schema, run_doc, step_index, _has_file, prog_mode), (
                document_bytes,
                file_size,
            ) in zip(pending, fetched, strict=True)
        ]

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
            )
        )
    return jobs


async def _persist_extraction_pair(
    session: AsyncSession,
    state: RunPhaseState,
    job: DocExtractionJob,
    extraction: ExtractionResult,
) -> None:
    state.fields_extracted += sum(1 for field in extraction.fields if field.extracted)
    state.extraction_results.append((job.doc.document_type, extraction))
    step_id = f"extract-{job.doc.id}"
    if extraction.meta:
        job.run_doc.extraction_meta = meta_to_dict(extraction.meta)
        state.extraction_total_ms += extraction.meta.extraction_ms
        mark_step_done(
            state.progress_steps,
            step_id,
            duration_ms=extraction.meta.extraction_ms,
            detail=extraction_step_detail(extraction.meta),
        )
    for field in extraction.fields:
        session.add(
            ExtractedField(
                id=new_id("fld"),
                run_document_id=job.run_doc.id,
                key=field.key,
                description=field.description,
                value=field.value,
                type=field.type,
                confidence=field.confidence,
                extracted=field.extracted,
                flagged=False,
            )
        )


async def run_extraction_phase(session: AsyncSession, state: RunPhaseState) -> None:
    """Extract all documents and persist fields; leaves run in running status."""
    storage = get_storage()
    settings = get_settings()
    run = state.run
    workflow_docs = state.workflow_docs
    rules_payload = state.rules_payload
    progress_steps = state.progress_steps
    run_id = state.run_id

    await set_run_progress(session, run_id, progress_steps, 1, "Starting audit run…", force=True)

    existing_run_docs = {rd.document_id: rd for rd in run.documents if rd.document_id}
    run_validation_mode = resolve_run_validation_mode(rules_payload)

    pending: list[PendingFetch] = []

    for doc in workflow_docs:
        schema = [
            SchemaFieldSpec(
                name=f.name,
                description=f.description,
                template_type=getattr(f, "template_type", None),
            )
            for f in sorted(doc.schema_fields, key=lambda x: x.position)
            if f.name.strip()
        ]
        if not schema:
            continue

        state.step_index += 1
        has_file = doc.id in state.docs_with_files
        prog_mode = progress_mode(doc, has_file=has_file)

        run_doc = existing_run_docs.get(doc.id)
        if not run_doc:
            run_doc = RunDocument(
                id=new_id("rdoc"),
                run_id=run.id,
                document_id=doc.id,
                document_type=doc.document_type,
            )
            session.add(run_doc)
            await session.flush()
            existing_run_docs[doc.id] = run_doc
        elif not run_doc.document_type:
            run_doc.document_type = doc.document_type

        pending.append((doc, schema, run_doc, state.step_index, has_file, prog_mode))

    if not pending:
        state.validation_mode = resolve_run_validation_mode(rules_payload)
        return

    use_parallel = effective_parallel_doc_extraction(settings) and len(pending) > 1

    jobs = await _build_extraction_jobs(
        storage,
        pending,
        parallel=use_parallel,
        parallel_fetch=settings.parallel_storage_fetch,
        validation_mode=run_validation_mode,
    )

    if use_parallel:
        for job in jobs:
            if is_serverless_vllm() and job.progress_mode == "document_model":
                _annotate_cold_start_hint(progress_steps, f"extract-{job.doc.id}")
        await set_run_progress(
            session,
            run_id,
            progress_steps,
            jobs[0].step_index,
            f"Extracting {len(jobs)} documents in parallel…",
            force=True,
        )
        pairs = await asyncio.gather(*[_run_extraction(job) for job in jobs])
    else:
        pairs = []
        for idx, job in enumerate(jobs):
            read_label = read_path_used_label(parse_read_path(job.doc.extraction_mode or "auto").id)
            val_label = validation_mode_label(job.validation_mode)
            step_id = f"extract-{job.doc.id}"
            detail = f"{read_label} · {val_label}"
            if is_serverless_vllm() and job.progress_mode == "document_model":
                detail = f"{detail} · {_GPU_COLD_START_DETAIL}"
                _annotate_cold_start_hint(progress_steps, step_id)
            await set_run_progress(
                session,
                run_id,
                progress_steps,
                job.step_index,
                extract_label(
                    job.doc.document_type,
                    mode=job.progress_mode,
                    detail=detail,
                ),
                force=(idx == 0 or idx == len(jobs) - 1),
            )
            pairs.append(await _run_extraction(job))

    for job, extraction in pairs:
        await _persist_extraction_pair(session, state, job, extraction)
        job.document_bytes = None

    state.validation_mode = resolve_run_validation_mode(rules_payload)
    await session.flush()
