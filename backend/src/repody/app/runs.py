"""Run use cases: start a run with its files, read its state, list, export and purge audits."""

import asyncio
import csv
import json
from collections import OrderedDict
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, BinaryIO

import structlog
from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from repody.app import credits
from repody.app.errors import AppError
from repody.app.lifecycle import fail
from repody.app.progress import plan, stored
from repody.app.scope import visible_runs
from repody.app.stats import midnight
from repody.extraction.render import FileInfo, inspect, page_preview
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

log = structlog.get_logger(__name__)

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


def _inspect(upload: Upload) -> FileInfo:
    """What the file is, by its content (see ``render.inspect``), if that type is allowed, and
    its page count. Blocking: call it in a thread."""
    allowed = get_settings().upload_allowed_mime_types
    info = inspect(upload.file)
    if info is None or info.mime not in allowed:
        raise AppError(
            422, f"{upload.file_name}: unsupported file type. Allowed: {', '.join(allowed)}."
        )
    return info


def _pages(definition: WorkflowDefinition, document_ids: list[str], files: list[FileInfo]) -> int:
    """The pages the run will send the model: its documents that are extracted, each up to
    AUDIT_MAX_PAGES_PER_DOCUMENT."""
    settings = get_settings()
    extracted = {doc.id for doc in definition.documents if doc.wants_extraction}
    cap = settings.max_pages_per_document
    pages = sum(
        min(info.pages, cap or info.pages)
        for document_id, info in zip(document_ids, files, strict=True)
        if document_id in extracted
    )
    if settings.max_pages_per_run and pages > settings.max_pages_per_run:
        log.warning("run_refused_too_many_pages", pages=pages, limit=settings.max_pages_per_run)
        raise AppError(
            422, f"{pages} pages to read: a run reads at most {settings.max_pages_per_run}."
        )
    return pages


async def _started(session: AsyncSession, client_key: str, idempotency_key: str) -> str | None:
    """The run a client already started with this Idempotency-Key."""
    return await session.scalar(
        select(Run.id).where(Run.client_key == client_key, Run.idempotency_key == idempotency_key)
    )


async def start_run(
    session: AsyncSession,
    wf: Workflow,
    *,
    source: Source,
    uploads: list[Upload],
    slots: list[str],
    client_key: str,
    definition: WorkflowDefinition | None = None,
    idempotency_key: str | None = None,
) -> RunCreated:
    """Store the files, queue the run with a copy of the definition, and send it to a worker.

    ``definition`` (a builder draft) is only honoured for test runs; API runs use the
    deployed workflow. The run holds its estimate on its account's credits (402 when it cannot
    pay, repody.app.credits). The files are stored before the transaction that saves the run
    (no database connection waits on S3), and deleted again when the run cannot be saved. A
    retry with the same ``idempotency_key`` returns the run it started.
    """
    settings = get_settings()
    if idempotency_key and (started := await _started(session, client_key, idempotency_key)):
        log.info("run_start_replayed", run_id=started)
        return RunCreated(run_id=started)
    if source == "api" and not wf.deployed_at:
        raise AppError(409, "Workflow is not deployed.")
    if len(uploads) > settings.max_upload_files:
        raise AppError(422, f"At most {settings.max_upload_files} files per run.")
    for upload in uploads:
        _check_upload(upload)
    await _check_queue(session)

    if source == "api" or definition is None:
        definition = WorkflowDefinition.model_validate(wf.definition)
    document_ids = _document_ids(definition, slots, len(uploads))
    files = [await asyncio.to_thread(_inspect, upload) for upload in uploads]
    types = {doc.id: doc.document_type for doc in definition.documents}
    account = credits.payer(wf.account_id)
    cost = credits.run_cost(_pages(definition, document_ids, files))
    await credits.can_pay(session, account, cost)
    await session.commit()  # end the read transaction before the uploads
    log.info("run_starting", workflow_id=wf.id, account=account, source=source, estimate=cost)

    run = Run(
        id=new_id("run"),
        workflow_id=wf.id,
        source=source,
        definition=definition.model_dump(),
        account_id=wf.account_id,
        client_key=client_key,
        idempotency_key=idempotency_key,
    )
    stored: list[str] = []
    try:
        for position, (upload, document_id, info) in enumerate(
            zip(uploads, document_ids, files, strict=True)
        ):
            key = f"runs/{run.id}/{position}"
            await get_store().put(key, upload.file, info.mime)
            stored.append(key)
            run.documents.append(
                RunDocument(
                    id=new_id("rdoc"),
                    position=position,
                    document_id=document_id,
                    document_type=types[document_id],
                    file_name=upload.file_name[:255],
                    mime_type=info.mime,
                    storage_key=key,
                )
            )
        run.progress = plan(definition, set(document_ids)).model_dump()
        session.add(run)
        await credits.hold(session, run, account, cost, client_key)
        await session.commit()
    except IntegrityError:
        # The same Idempotency-Key at the same time: the other request saved its run.
        await session.rollback()
        await get_store().delete(stored)
        if idempotency_key and (started := await _started(session, client_key, idempotency_key)):
            return RunCreated(run_id=started)
        raise
    except BaseException:
        await get_store().delete(stored)
        raise
    try:
        run.task_run_id = await queue.dispatch(run.id, client_key)
    except Exception as exc:
        log.warning("run_dispatch_failed", run_id=run.id, error=repr(exc))
        await fail(session, run.id, "The run could not be queued.")
        await session.commit()
        raise AppError(
            503, "The run queue is unavailable; try again shortly.", retry_after=15
        ) from exc
    await session.commit()
    return RunCreated(run_id=run.id)


# --- Read a run ---


async def _load_run(session: AsyncSession, run_id: str, account: str | None) -> Run:
    run = await session.scalar(
        select(Run)
        .where(Run.id == run_id, visible_runs(account))
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


async def run_state(session: AsyncSession, run_id: str, *, account: str | None = None) -> RunState:
    run = await _load_run(session, run_id, account)
    return RunState(
        status=run.status,
        progress=stored(run),
        error=run.error,
        result=_report(run) if run.status == "done" else None,
    )


async def run_report(
    session: AsyncSession, run_id: str, *, account: str | None = None
) -> AuditDetail:
    run = await _load_run(session, run_id, account)
    if run.status != "done":
        raise AppError(404, "Audit not found.")
    return _report(run)


# Pages recently shown, by (document, page): a report's pages are opened again and again, and
# each render downloads the whole file and takes PDFium's process-wide lock.
_PREVIEWS: OrderedDict[tuple[str, int], bytes] = OrderedDict()
PREVIEW_CACHE = 64  # a few hundred KB each


async def document_page(
    session: AsyncSession,
    run_id: str,
    document_id: str,
    page: int,
    *,
    account: str | None = None,
) -> bytes:
    """One page of a run's uploaded document, as WebP for the report."""
    doc = await session.scalar(
        select(RunDocument)
        .join(Run, Run.id == RunDocument.run_id)
        .where(RunDocument.run_id == run_id, RunDocument.id == document_id, visible_runs(account))
    )
    if doc is None:
        raise AppError(404, "Document not found.")
    if (image := _PREVIEWS.get((doc.id, page))) is not None:
        _PREVIEWS.move_to_end((doc.id, page))
        return image
    data = await get_store().get(doc.storage_key)
    image = await asyncio.to_thread(page_preview, data, doc.mime_type, page)
    if image is None:
        raise AppError(404, "Page not found.")
    _PREVIEWS[doc.id, page] = image
    if len(_PREVIEWS) > PREVIEW_CACHE:
        _PREVIEWS.popitem(last=False)
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


def _audits(audits: AuditFilter, account: str | None) -> Select[Run]:
    """Done runs matching the filter, newest first, each with its workflow (one join)."""
    query = (
        select(Run)
        .join(Run.workflow)
        .options(
            contains_eager(Run.workflow),
            selectinload(Run.documents).load_only(RunDocument.file_name, RunDocument.position),
            selectinload(Run.rule_results).load_only(RuleResult.name, RuleResult.status),
        )
        .where(Run.status == "done", visible_runs(account))
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
        query = query.where(
            or_(Run.id.icontains(q, autoescape=True), Workflow.name.icontains(q, autoescape=True))
        )
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


async def list_audits(
    session: AsyncSession, page: AuditPage, *, account: str | None = None
) -> AuditList:
    query = _audits(page, account)
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
    """One CSV line; a text cell a spreadsheet would run as a formula gets a leading apostrophe,
    also when spaces come first (some spreadsheets trim them)."""
    cells = (
        f"'{cell}"
        if isinstance(cell, str) and cell.lstrip(" ").startswith(FORMULA_PREFIXES)
        else cell
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


async def export_audits(
    session: AsyncSession, audits: AuditFilter, *, account: str | None = None
) -> AsyncIterator[str]:
    """Every matching audit as CSV, streamed from a server-side cursor (no row limit)."""
    yield BOM + _csv_line(AUDIT_COLUMNS)
    runs = await session.stream_scalars(
        _audits(audits, account).execution_options(yield_per=EXPORT_BATCH)
    )
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


async def export_report(session: AsyncSession, run_id: str, *, account: str | None = None) -> str:
    """One audit as a table: one row per extracted field, then one per rule result."""
    report = await run_report(session, run_id, account=account)
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
