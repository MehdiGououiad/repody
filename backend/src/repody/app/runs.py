"""Run use cases: start a run with its files, read its state, list finished runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

import filetype
import structlog
from limits import parse
from limits.aio.storage import RedisStorage
from limits.aio.strategies import MovingWindowRateLimiter
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.app.errors import AppError
from repody.app.progress import plan, publish, with_queue_position
from repody.infra import db, queue
from repody.infra.models import Run, RunDocument, Workflow, new_id
from repody.infra.storage import get_store
from repody.schemas.run import (
    AuditDetail,
    AuditDocument,
    AuditList,
    AuditListItem,
    AuditRule,
    RunCreated,
    RunState,
    RunSummary,
    RunTimings,
)
from repody.schemas.workflow import WorkflowDefinition
from repody.settings import get_settings

log = structlog.get_logger(__name__)

Source = Literal["test", "api"]


@dataclass(frozen=True, slots=True)
class Upload:
    file_name: str
    data: bytes


@lru_cache
def _limiter() -> MovingWindowRateLimiter:
    return MovingWindowRateLimiter(RedisStorage(get_settings().redis_url))


async def _check_rate(client_key: str) -> None:
    per_minute = get_settings().runs_per_minute_per_client
    if per_minute and not await _limiter().hit(parse(f"{per_minute}/minute"), "runs", client_key):
        raise AppError(429, "Too many runs started; try again in a minute.", retry_after=60)


async def _check_queue(session: AsyncSession) -> None:
    cap = get_settings().max_queued_runs
    queued = await session.scalar(select(func.count()).where(Run.status == "queued")) or 0
    if cap and queued >= cap:
        raise AppError(503, f"The queue is full ({queued} runs waiting).", retry_after=15)


def _document_ids(definition: WorkflowDefinition, slots: list[str], count: int) -> list[str]:
    """The workflow document each file belongs to: ``slots`` name each file's document by id
    or document type; without slots, files fill the documents in order."""
    docs = definition.documents
    if not slots:
        if count > len(docs):
            raise AppError(422, f"{count} files for {len(docs)} workflow documents.")
        return [doc.id for doc in docs[:count]]
    if len(slots) != count:
        raise AppError(422, "Give one document id or type per uploaded file.")
    ids: list[str] = []
    for slot in slots:
        key = slot.strip().casefold()
        matches = [d.id for d in docs if slot == d.id or d.document_type.casefold() == key]
        if len(matches) != 1:
            raise AppError(422, f"Unknown or ambiguous document {slot!r}: use its id or type.")
        ids.append(matches[0])
    return ids


def _mime(upload: Upload) -> str:
    allowed = get_settings().upload_allowed_mime_types
    mime = filetype.guess_mime(upload.data)
    if mime not in allowed:
        raise AppError(
            422, f"{upload.file_name}: unsupported file type. Allowed: {', '.join(allowed)}."
        )
    return mime


async def start_run(
    session: AsyncSession,
    wf: Workflow,
    *,
    source: Source,
    uploads: list[Upload],
    slots: list[str],
    client_key: str,
    definition: WorkflowDefinition | None = None,
) -> RunCreated:
    """Store the files, queue the run with a copy of the definition, and send it to a worker.

    ``definition`` (a builder draft) is only honoured for test runs; API runs use the
    deployed workflow.
    """
    settings = get_settings()
    if source == "api" and not wf.deployed_at:
        raise AppError(409, "Workflow is not deployed.")
    if len(uploads) > settings.max_upload_files:
        raise AppError(422, f"At most {settings.max_upload_files} files per run.")
    await _check_rate(client_key)
    await _check_queue(session)

    if source == "api" or definition is None:
        definition = WorkflowDefinition.model_validate(wf.definition)
    document_ids = _document_ids(definition, slots, len(uploads))
    mimes = [_mime(upload) for upload in uploads]
    types = {doc.id: doc.document_type for doc in definition.documents}

    run = Run(
        id=new_id("AUD"), workflow_id=wf.id, source=source, definition=definition.model_dump()
    )
    files = zip(uploads, document_ids, mimes, strict=True)
    for position, (upload, document_id, mime) in enumerate(files):
        key = f"runs/{run.id}/{position}"
        await get_store().put(key, upload.data, mime)
        run.documents.append(
            RunDocument(
                id=new_id("rdoc"),
                position=position,
                document_id=document_id,
                document_type=types[document_id],
                file_name=upload.file_name[:255],
                mime_type=mime,
                storage_key=key,
            )
        )
    run.progress = plan(definition, set(document_ids)).model_dump()
    session.add(run)
    await session.commit()
    await queue.dispatch(run.id)
    return RunCreated(run_id=run.id)


async def fail_run(run_id: str, error: str, *, only_if: str | None = None) -> bool:
    """Mark a queued or running run failed (``only_if`` narrows the expected status)."""
    async with db.session_factory() as session:
        condition = Run.status == only_if if only_if else Run.status.in_(("queued", "running"))
        failed = await session.execute(
            update(Run)
            .where(Run.id == run_id, condition)
            .values(status="failed", error=error[:4000], finished_at=datetime.now(UTC))
            .returning(Run.id)
        )
        if failed.scalar_one_or_none() is None:
            return False
        await session.commit()
    await publish(run_id, {"terminal": True, "status": "failed", "error": error[:500]})
    log.warning("run_failed", run_id=run_id, error=error[:200])
    return True


async def _load_run(session: AsyncSession, run_id: str) -> Run:
    run = await session.scalar(
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.workflow),
            selectinload(Run.documents).selectinload(RunDocument.fields),
            selectinload(Run.rule_results),
        )
    )
    if run is None:
        raise AppError(404, "Run not found.")
    return run


def _report(run: Run) -> AuditDetail:
    duration = (
        int((run.finished_at - run.started_at).total_seconds() * 1000)
        if run.started_at and run.finished_at
        else 0
    )
    return AuditDetail(
        id=run.id,
        workflow_id=run.workflow_id,
        workflow_name=run.workflow.name,
        status=run.outcome or "warning",  # type: ignore[arg-type]
        source=run.source,
        created_at=run.created_at,
        documents=[AuditDocument.model_validate(doc) for doc in run.documents],
        rule_results=[AuditRule.model_validate(rule) for rule in run.rule_results],
        summary=RunSummary(
            total=run.rules_total,
            passed=run.rules_passed,
            failed=run.rules_failed,
            fields_extracted=run.fields_extracted,
        ),
        metadata=RunTimings(
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_ms=duration,
            extraction_ms=run.extraction_ms,
            validation_ms=run.validation_ms,
        ),
    )


async def run_state(session: AsyncSession, run_id: str) -> RunState:
    run = await _load_run(session, run_id)
    return RunState(
        status=run.status,  # type: ignore[arg-type]
        progress=await with_queue_position(session, run),
        error=run.error,
        result=_report(run) if run.status == "done" else None,
    )


async def run_report(session: AsyncSession, run_id: str) -> AuditDetail:
    run = await _load_run(session, run_id)
    if run.status != "done":
        raise AppError(404, "Audit not found.")
    return _report(run)


async def run_api_key_hash(session: AsyncSession, run_id: str) -> str | None:
    """Hash of the API key of the run's workflow (None for an unknown run or no key)."""
    return await session.scalar(
        select(Workflow.api_key_hash)
        .join(Run, Run.workflow_id == Workflow.id)
        .where(Run.id == run_id)
    )


async def list_audits(session: AsyncSession, *, limit: int = 50, offset: int = 0) -> AuditList:
    limit, offset = max(1, min(limit, 200)), max(0, offset)
    done = Run.status == "done"
    runs = await session.scalars(
        select(Run)
        .where(done)
        .order_by(Run.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(selectinload(Run.workflow))
    )
    return AuditList(
        audits=[audit_item(run) for run in runs],
        total=await session.scalar(select(func.count()).where(done)) or 0,
        limit=limit,
        offset=offset,
    )


def audit_item(run: Run) -> AuditListItem:
    return AuditListItem(
        id=run.id,
        status=run.outcome or "warning",  # type: ignore[arg-type]
        workflow_id=run.workflow_id,
        workflow_name=run.workflow.name,
        timestamp=run.created_at,
        rows=run.fields_extracted,
        failed_rules=run.rules_failed,
    )
