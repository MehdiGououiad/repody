"""Document extraction phase for audit runs."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import ExtractedField, RunDocument
from audit_workbench.extraction.base import ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.document_modes import (
    DEFAULT_READ_PATH_ID,
    document_needs_extraction,
    parse_read_path,
    read_path_used_label,
    resolve_run_validation_mode,
    validation_mode_label,
)
from audit_workbench.extraction.gpu_cold_start import is_serverless_vllm
from audit_workbench.inference.runtime import effective_parallel_doc_extraction
from audit_workbench.services.run.extraction_jobs import (
    DocExtractionJob,
    PendingFetch,
    build_extraction_jobs,
    run_extraction_job,
)
from audit_workbench.services.run.helpers import (
    extraction_step_detail,
    extract_label,
    meta_to_dict,
    new_id,
    progress_mode,
)
from audit_workbench.services.run.phase_state import RunPhaseState
from audit_workbench.services.run.progress_persist import set_run_progress
from audit_workbench.services.run.progress_plan import mark_step_done
from audit_workbench.settings import get_settings
from audit_workbench.storage.factory import get_storage

_GPU_COLD_START_DETAIL = "Serverless GPU may need 1-2 min to start on the first request after idle"


async def persist_extraction_pair(
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
            cache_hit=extraction.meta.cache_hit,
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


def _annotate_cold_start_hint(steps: list, step_id: str) -> None:
    if not is_serverless_vllm():
        return
    for step in steps:
        if step.get("id") == step_id:
            step["gpuColdStartHint"] = True
            break


def _schema_for_doc(doc) -> list[SchemaFieldSpec]:
    return [
        SchemaFieldSpec(
            name=field.name,
            description=field.description,
            template_type=getattr(field, "template_type", None),
        )
        for field in sorted(doc.schema_fields, key=lambda item: item.position)
        if field.name.strip()
    ]


async def run_extraction_phase(session: AsyncSession, state: RunPhaseState) -> None:
    """Extract all documents and persist fields; leaves run in running status."""
    storage = get_storage()
    settings = get_settings()
    run = state.run
    workflow_docs = state.workflow_docs
    rules_payload = state.rules_payload
    progress_steps = state.progress_steps
    run_id = state.run_id

    await set_run_progress(session, run_id, progress_steps, 1, "Starting audit run\u2026", force=True)

    existing_run_docs = {rd.document_id: rd for rd in run.documents if rd.document_id}
    run_validation_mode = resolve_run_validation_mode(rules_payload)

    pending: list[PendingFetch] = []

    for doc in workflow_docs:
        has_file = doc.id in state.docs_with_files
        if not document_needs_extraction(doc, has_file=has_file):
            continue

        schema = _schema_for_doc(doc)
        state.step_index += 1
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

    jobs = await build_extraction_jobs(
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
            f"Extracting {len(jobs)} documents in parallel\u2026",
            force=True,
        )
        pairs = await asyncio.gather(*[run_extraction_job(job) for job in jobs])
    else:
        pairs = []
        for idx, job in enumerate(jobs):
            read_label = read_path_used_label(parse_read_path(job.doc.extraction_mode or DEFAULT_READ_PATH_ID).id)
            val_label = validation_mode_label(job.validation_mode)
            step_id = f"extract-{job.doc.id}"
            detail = f"{read_label} \u00b7 {val_label}"
            if is_serverless_vllm() and job.progress_mode == "document_model":
                detail = f"{detail} \u00b7 {_GPU_COLD_START_DETAIL}"
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
            pairs.append(await run_extraction_job(job))

    for job, extraction in pairs:
        await persist_extraction_pair(session, state, job, extraction)
        job.document_bytes = None

    state.validation_mode = resolve_run_validation_mode(rules_payload)
    await session.flush()
