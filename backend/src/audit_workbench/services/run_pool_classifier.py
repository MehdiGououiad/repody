"""Classify audit runs into Hatchet worker pools (ocr | fast)."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import Run, Workflow
from audit_workbench.extraction.processing_paths import parse_read_path

WorkerPool = str  # "ocr" | "fast"

_OCR_READ_KINDS = frozenset({"document_model"})


class FileBindingLike(Protocol):
    document_id: str | None


def needs_ocr_pool(extraction_mode: str | None) -> bool:
    read = parse_read_path(extraction_mode).read
    return read in _OCR_READ_KINDS


def classify_bindings_for_workflow(
    workflow_docs: list[Any],
    file_bindings: list[FileBindingLike] | None,
) -> WorkerPool:
    """Predict pool from workflow document modes and upload bindings."""
    if not file_bindings:
        return "fast"

    wf_doc_by_id = {_value(doc, "id"): doc for doc in workflow_docs}
    for binding in file_bindings:
        doc_id = getattr(binding, "document_id", None)
        wf_doc = wf_doc_by_id.get(doc_id or "") if doc_id else None
        mode = _value(wf_doc, "extraction_mode", "auto") if wf_doc else "auto"
        if needs_ocr_pool(mode):
            return "ocr"
    return "fast"


def classify_run_documents(
    workflow_docs: list[Any],
    run_documents: list[Any],
) -> WorkerPool:
    """Classify an existing run from persisted run documents."""
    uploaded = [rd for rd in run_documents if _value(rd, "storage_key")]
    if not uploaded:
        return "fast"

    wf_doc_by_id = {_value(doc, "id"): doc for doc in workflow_docs}
    for rd in uploaded:
        doc_id = _value(rd, "document_id")
        wf_doc = wf_doc_by_id.get(doc_id or "") if doc_id else None
        mode = _value(wf_doc, "extraction_mode", "auto") if wf_doc else "auto"
        if needs_ocr_pool(mode):
            return "ocr"
    return "fast"


def _value(item: Any, key: str, default: Any = None) -> Any:
    value = getattr(item, key, None)
    if value is not None:
        return value
    if isinstance(item, dict):
        return item.get(key, default)
    return default


async def predict_worker_pool(
    session: AsyncSession,
    workflow_id: str,
    *,
    file_bindings: list | None = None,
) -> WorkerPool:
    """Predict Hatchet pool before a run row exists (admission / enqueue)."""
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
    return classify_bindings_for_workflow(wf.documents, file_bindings)


async def resolve_worker_pool(session: AsyncSession, run_id: str) -> WorkerPool:
    """Resolve pool for a persisted run (dispatch fallback)."""
    run = (
        await session.execute(
            select(Run)
            .where(Run.id == run_id)
            .options(selectinload(Run.documents))
        )
    ).scalar_one_or_none()
    if not run:
        return "fast"
    if run.worker_pool:
        return run.worker_pool

    wf = (
        await session.execute(
            select(Workflow)
            .where(Workflow.id == run.workflow_id)
            .options(selectinload(Workflow.documents))
        )
    ).scalar_one_or_none()
    if not wf:
        return "ocr"
    return classify_run_documents(wf.documents, run.documents)
