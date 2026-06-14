from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import Run, Workflow
from audit_workbench.extraction.processing_paths import parse_read_path

_OCR_READ_KINDS = frozenset({"document_model"})


def needs_ocr_pool(extraction_mode: str | None) -> bool:
    read = parse_read_path(extraction_mode).read
    return read in _OCR_READ_KINDS


async def resolve_worker_pool(session: AsyncSession, run_id: str) -> str:
    """
    Fast pool: no files, or paths that do not require document-model inference.

    OCR pool: document-model extraction on uploaded documents.
    """
    run = (
        await session.execute(
            select(Run)
            .where(Run.id == run_id)
            .options(selectinload(Run.documents))
        )
    ).scalar_one_or_none()
    if not run:
        return "fast"

    uploaded = [rd for rd in run.documents if rd.storage_key]
    if not uploaded:
        return "fast"

    wf = (
        await session.execute(
            select(Workflow)
            .where(Workflow.id == run.workflow_id)
            .options(selectinload(Workflow.documents))
        )
    ).scalar_one_or_none()
    if not wf:
        return "ocr"

    wf_doc_by_id = {d.id: d for d in wf.documents}
    for rd in uploaded:
        wf_doc = wf_doc_by_id.get(rd.document_id or "") if rd.document_id else None
        mode = wf_doc.extraction_mode if wf_doc else "auto"
        if needs_ocr_pool(mode):
            return "ocr"

    return "fast"


async def predict_worker_pool(
    session: AsyncSession,
    workflow_id: str,
    *,
    file_bindings: list | None = None,
) -> str:
    """Predict Hatchet pool before a run row exists (admission control)."""
    if not file_bindings:
        return "fast"

    wf = (
        await session.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.documents))
        )
    ).scalar_one_or_none()
    if not wf:
        return "ocr"

    wf_doc_by_id = {d.id: d for d in wf.documents}
    for binding in file_bindings:
        doc_id = getattr(binding, "document_id", None)
        wf_doc = wf_doc_by_id.get(doc_id or "") if doc_id else None
        mode = wf_doc.extraction_mode if wf_doc else "auto"
        if needs_ocr_pool(mode):
            return "ocr"

    return "fast"
