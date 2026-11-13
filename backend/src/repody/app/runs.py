"""Run use cases: start a run with its files, read its state, list, export and purge audits."""

import asyncio
import csv
import json
import math
import time
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any, BinaryIO

from limits import RateLimitItemPerMinute
from limits.aio.storage import RedisStorage
from limits.aio.strategies import SlidingWindowCounterRateLimiter
from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from repody.app.errors import AppError
from repody.app.progress import plan, with_queue_position
from repody.app.stats import midnight
from repody.extraction.render import file_type, page_preview
from repody.infra import db, queue
from repody.infra.models import RuleResult, Run, RunDocument, Workflow, new_id
from repody.infra.storage import get_store
from repody.schemas.run import (
    REVIEW_OUTCOMES,
    AuditDetail,
    AuditDocument,
    AuditFilter,
    AuditList,
    AuditListItem,
    AuditPage,
    AuditRule,
    Outcome,
    RunCreated,
    RunState,
    RunSummary,
    RunTimings,
    Source,
)
from repody.schemas.workflow import WorkflowDefinition
from repody.settings import get_settings

EXPORT_BATCH = 500  # rows fetched per round trip while streaming a CSV export
PURGE_BATCH = 1000  # runs deleted per transaction by the retention purge
BOM = "﻿"  # spreadsheets read a UTF-8 CSV as UTF-8 when it starts with a BOM
# A spreadsheet runs a cell starting with these as a formula (OWASP "CSV Injection").
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True, slots=True)
class Upload:
    """An uploaded file, read from its (spooled) stream when stored."""

    file_name: str
    file: BinaryIO
    size: int


# --- Start a run ---


@cache
def _limiter() -> SlidingWindowCounterRateLimiter:
    # redis-py, the client the rest of the backend uses (limits defaults to coredis). The
    # sliding window counter is the strategy limits recommends: approximate, two keys per client.
    redis_url = get_settings().redis_url.get_secret_value()
    storage = RedisStorage(f"async+{redis_url}", implementation="redispy")
    return SlidingWindowCounterRateLimiter(storage)


async def _check_rate(client_key: str) -> None:
    per_minute = get_settings().runs_per_minute_per_client
    if not per_minute:
        return
    limit = RateLimitItemPerMinute(per_minute)
    if not await _limiter().hit(limit, "runs", client_key):
        stats = await _limiter().get_window_stats(limit, "runs", client_key)
        retry_after = max(1, math.ceil(stats.reset_time - time.time()))
        raise AppError(429, "Too many runs started; try again shortly.", retry_after=retry_after)


async def _check_queue(session: AsyncSession) -> None:
    cap = get_settings().max_queued_runs
    queued = await session.scalar(select(func.count()).where(Run.status == "queued")) or 0
    if cap and queued >= cap:
        raise AppError(503, f"The queue is full ({queued} runs waiting).", retry_after=15)


def _check_upload(upload: Upload) -> None:
    limit = get_settings().max_upload_bytes
    if upload.size > limit:
        raise AppError(413, f"{upload.file_name} is larger than {limit} bytes.")
    if upload.size == 0:
        raise AppError(422, f"{upload.file_name} is empty.")


def _document_ids(definition: WorkflowDefinition, slots: list[str], count: int) -> list[str]:
    """The workflow document each file belongs to, one file per document: ``slots`` name each
    file's document by id or document type; without slots, files fill the documents in order."""
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
        if matches[0] in ids:
            raise AppError(422, f"Document {slot!r} has more than one file: send one per document.")
        ids.append(matches[0])
    return ids


def _mime(upload: Upload) -> str:
    """What the file is, by its content (see ``render.file_type``), if that type is allowed."""
    allowed = get_settings().upload_allowed_mime_types
    mime = file_type(upload.file)
    if mime is None or mime not in allowed:
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
    deployed workflow. Files stored for a run that cannot be saved are deleted again.
    """
    settings = get_settings()
    if source == "api" and not wf.deployed_at:
        raise AppError(409, "Workflow is not deployed.")
    if len(uploads) > settings.max_upload_files:
        raise AppError(422, f"At most {settings.max_upload_files} files per run.")
    for upload in uploads:
        _check_upload(upload)
    await _check_rate(client_key)
    await _check_queue(session)

    if source == "api" or definition is None:
        definition = WorkflowDefinition.model_validate(wf.definition)
    document_ids = _document_ids(definition, slots, len(uploads))
    mimes = [_mime(upload) for upload in uploads]
    types = {doc.id: doc.document_type for doc in definition.documents}

    run = Run(
        id=new_id("run"), workflow_id=wf.id, source=source, definition=definition.model_dump()
    )
    stored: list[str] = []
    try:
        files = zip(uploads, document_ids, mimes, strict=True)
        for position, (upload, document_id, mime) in enumerate(files):
            key = f"runs/{run.id}/{position}"
            await get_store().put(key, upload.file, mime)
            stored.append(key)
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
    except BaseException:
        await get_store().delete(stored)
        raise
    await queue.dispatch(run.id)
    return RunCreated(run_id=run.id)


# --- Read a run ---


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


def _outcome(run: Run) -> Outcome:
    """The result of a done run; only done runs have one (CHECK ck_runs_outcome_when_done)."""
    if run.outcome is None:
        raise ValueError(f"Run {run.id} is {run.status}: it has no report.")
    return run.outcome


def _report(run: Run) -> AuditDetail:
    duration = _duration_ms(run)
    return AuditDetail(
        id=run.id,
        workflow_id=run.workflow_id,
        workflow_name=run.workflow.name,
        status=_outcome(run),
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
        status=run.status,
        progress=await with_queue_position(session, run),
        error=run.error,
        result=_report(run) if run.status == "done" else None,
    )


async def run_report(session: AsyncSession, run_id: str) -> AuditDetail:
    run = await _load_run(session, run_id)
    if run.status != "done":
        raise AppError(404, "Audit not found.")
    return _report(run)


async def document_page(session: AsyncSession, run_id: str, document_id: str, page: int) -> bytes:
    """One page of a run's uploaded document, as WebP for the report."""
    doc = await session.scalar(
        select(RunDocument).where(RunDocument.run_id == run_id, RunDocument.id == document_id)
    )
    if doc is None:
        raise AppError(404, "Document not found.")
    data = await get_store().get(doc.storage_key)
    image = await asyncio.to_thread(page_preview, data, doc.mime_type, page)
    if image is None:
        raise AppError(404, "Page not found.")
    return image


async def run_api_key_hash(session: AsyncSession, run_id: str) -> str | None:
    """Hash of the API key of the run's workflow; None for an unknown run, a workflow without
    a key, or an archived workflow (its key no longer works)."""
    return await session.scalar(
        select(Workflow.api_key_hash)
        .join(Run, Run.workflow_id == Workflow.id)
        .where(Run.id == run_id, Workflow.status != "archived")
    )


# --- Audits: finished runs ---


def _audits(audits: AuditFilter) -> Select[Run]:
    """Done runs matching the filter, newest first, each with its workflow (one join)."""
    query = (
        select(Run)
        .join(Run.workflow)
        .options(
            contains_eager(Run.workflow),
            selectinload(Run.documents).load_only(RunDocument.file_name, RunDocument.position),
            selectinload(Run.rule_results).load_only(RuleResult.name, RuleResult.status),
        )
        .where(Run.status == "done")
        .order_by(Run.created_at.desc(), Run.id.desc())
    )
    if audits.outcome == "review":
        query = query.where(Run.outcome.in_(REVIEW_OUTCOMES))
    elif audits.outcome:
        query = query.where(Run.outcome == audits.outcome)
    if audits.workflow_id:
        query = query.where(Run.workflow_id == audits.workflow_id)
    if audits.day:
        start = midnight(audits.day)
        query = query.where(Run.created_at >= start, Run.created_at < start + timedelta(days=1))
    if q := audits.q.strip():
        pattern = f"%{q}%"
        query = query.where(or_(Run.id.ilike(pattern), Workflow.name.ilike(pattern)))
    return query


def _duration_ms(run: Run) -> int:
    if run.started_at and run.finished_at:
        return int((run.finished_at - run.started_at).total_seconds() * 1000)
    return 0


def audit_item(run: Run) -> AuditListItem:
    """Needs the run's documents and rule results loaded (``_audits`` does)."""
    failed = next((r.name for r in run.rule_results if r.status == "failed"), None)
    return AuditListItem(
        id=run.id,
        status=_outcome(run),
        workflow_id=run.workflow_id,
        workflow_name=run.workflow.name,
        source=run.source,
        timestamp=run.created_at,
        duration_ms=_duration_ms(run),
        rows=run.fields_extracted,
        failed_rules=run.rules_failed,
        files=[doc.file_name for doc in run.documents if doc.file_name],
        first_failed_rule=failed,
    )


async def list_audits(session: AsyncSession, page: AuditPage) -> AuditList:
    query = _audits(page)
    runs = await session.scalars(query.offset(page.offset).limit(page.limit))
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return AuditList(
        audits=[audit_item(run) for run in runs],
        total=total or 0,
        limit=page.limit,
        offset=page.offset,
    )


class _Echo:
    """A file-like object whose ``write`` returns what it is given, so ``csv.writer.writerow``
    returns the formatted line (the streaming CSV recipe)."""

    def write(self, line: str) -> str:
        return line


_CSV = csv.writer(_Echo())


def _csv_line(row: Iterable[Any]) -> str:
    """One CSV line; a text cell a spreadsheet would run as a formula gets a leading apostrophe."""
    cells = (
        f"'{cell}" if isinstance(cell, str) and cell.startswith(FORMULA_PREFIXES) else cell
        for cell in row
    )
    return str(_CSV.writerow(cells))


AUDIT_COLUMNS = [
    "id",
    "outcome",
    "workflow_id",
    "workflow",
    "created_at",
    "fields_extracted",
    "rules_failed",
]


async def export_audits(session: AsyncSession, audits: AuditFilter) -> AsyncIterator[str]:
    """Every matching audit as CSV, streamed from a server-side cursor (no row limit)."""
    yield BOM + _csv_line(AUDIT_COLUMNS)
    runs = await session.stream_scalars(_audits(audits).execution_options(yield_per=EXPORT_BATCH))
    async for run in runs:
        yield _csv_line(
            [
                run.id,
                run.outcome,
                run.workflow_id,
                run.workflow.name,
                run.created_at.isoformat(),
                run.fields_extracted,
                run.rules_failed,
            ]
        )


async def export_report(session: AsyncSession, run_id: str) -> str:
    """One audit as a table: one row per extracted field, then one per rule result."""
    report = await run_report(session, run_id)
    lines = [_csv_line(["section", "document", "name", "value", "type", "status", "detail"])]
    for doc in report.documents:
        error = (doc.extraction.error if doc.extraction else None) or ""
        for f in doc.fields:
            value = (
                json.dumps(f.value, ensure_ascii=False)
                if isinstance(f.value, list | dict)
                else f.value
            )
            status = "flagged" if f.flagged else ("extracted" if f.extracted else "missing")
            lines.append(
                _csv_line(["field", doc.document_type, f.key, value, f.type, status, error])
            )
    for r in report.rule_results:
        lines.append(_csv_line(["rule", "", r.name, r.expression, r.severity, r.status, r.detail]))
    return BOM + "".join(lines)


async def purge_expired() -> int:
    """Delete finished runs past AUDIT_RUN_RETENTION_DAYS and their stored files, in batches.

    Each batch deletes the runs' documents (collecting their storage keys) and the runs in one
    transaction, then their files; a file S3 fails to delete is logged by the store.
    """
    days = get_settings().run_retention_days
    if not days:
        return 0
    before = datetime.now(UTC) - timedelta(days=days)
    expired = select(Run.id).where(Run.status.in_(("done", "failed")), Run.created_at < before)
    purged = 0
    while True:
        async with db.session_factory() as session:
            ids = list(await session.scalars(expired.limit(PURGE_BATCH)))
            if not ids:
                return purged
            keys = list(
                await session.scalars(
                    delete(RunDocument)
                    .where(RunDocument.run_id.in_(ids))
                    .returning(RunDocument.storage_key)
                )
            )
            await session.execute(delete(Run).where(Run.id.in_(ids)))
            await session.commit()
        await get_store().delete(keys)
        purged += len(ids)
