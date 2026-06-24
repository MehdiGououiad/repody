"""Persistence helpers for extraction phase results."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import ExtractedField
from audit_workbench.extraction.base import ExtractionResult
from audit_workbench.services.run.extraction_jobs import DocExtractionJob
from audit_workbench.services.run.helpers import extraction_step_detail, meta_to_dict, new_id
from audit_workbench.services.run.phase_state import RunPhaseState
from audit_workbench.services.run_progress import mark_step_done


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
