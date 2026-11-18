"""Process one run on a worker: claim, extract the documents, check the rules, save the report.

Documents are extracted concurrently (bounded by AUDIT_INFERENCE_CONCURRENCY). A document
whose extraction fails keeps its error on the report and has no values (its rules are
skipped); any other error fails the run, and so does running past AUDIT_RUN_TIMEOUT_MINUTES
(Hatchet's execution timeout, see ``fail_unfinished``).
"""

import asyncio
import time
from datetime import UTC, datetime

import structlog
from sqlalchemy import update
from sqlalchemy.orm import selectinload, undefer

from repody.app import credits
from repody.app.lifecycle import fail_run, move_run
from repody.app.progress import FINALIZE_STEP, MODEL_STEP, RULES_STEP, Tracker, extract_step
from repody.extraction import client
from repody.extraction.pipeline import ModelRequestError, extract
from repody.infra import db
from repody.infra.models import ExtractedField, RuleResult, Run, RunDocument, new_id
from repody.infra.storage import get_store
from repody.rules.evaluate import RuleOutcome, evaluate_rules
from repody.schemas.catalog import field_key
from repody.schemas.run import ExtractionMeta, Outcome, RunProgress
from repody.schemas.workflow import DocumentDef, WorkflowDefinition
from repody.settings import get_settings

log = structlog.get_logger(__name__)

FAILURE_MESSAGE = "The run failed while processing. The worker logs have the details."
EXTRACTION_FAILED = (
    "Extraction failed: the model server did not answer or the file could not be read."
)


async def process_run(run_id: str) -> None:
    """The ``process-run`` task: run it to the end, or mark it failed. Its time limit is the
    Hatchet task's execution timeout (``repody.worker``): past it the task is cancelled and
    ``fail_unfinished`` records why."""
    with structlog.contextvars.bound_contextvars(run_id=run_id):
        try:
            await _process(run_id)
        except Exception:
            log.exception("run_processing_failed")
            await fail_run(run_id, FAILURE_MESSAGE)


async def fail_unfinished(run_id: str) -> None:
    """Hatchet gave up on the run's task (a timeout, a lost worker, a cancellation): fail the
    run if it is not finished, saying where it stopped."""
    minutes = get_settings().run_timeout_minutes
    if not await fail_run(
        run_id, "The run waited too long for a worker to start it.", only_if="queued"
    ):
        await fail_run(
            run_id,
            f"The run stopped before it finished (time limit {minutes} min, or its worker"
            " stopped).",
            only_if="running",
        )


async def _claim(run_id: str) -> bool:
    """Take the run: queued becomes running. A run already running is this task delivered again:
    Hatchet re-queues a task whose worker stopped heartbeating (it crashed, was killed at the end
    of a deploy's grace period, or the server restarted), so it starts over here; nothing of the
    lost attempt was saved but its progress. A finished run is never taken."""
    async with db.session_factory() as session:
        now = datetime.now(UTC)
        claimed = await move_run(session, run_id, "running", started_at=now)
        if not claimed:
            claimed = bool(
                await session.scalar(
                    update(Run)
                    .where(Run.id == run_id, Run.status == "running")
                    .values(started_at=now)
                    .returning(Run.id)
                )
            )
            if claimed:
                log.warning("run_redelivered")
        await session.commit()
        return claimed


async def _process(run_id: str) -> None:
    if not await _claim(run_id):
        log.info("run_already_finished")
        return
    async with db.session_factory() as session:
        run = await session.get_one(
            Run,
            run_id,
            options=[
                undefer(Run.definition),
                selectinload(Run.documents).selectinload(RunDocument.fields),
            ],
        )
        definition = WorkflowDefinition.model_validate(run.definition)
        tracker = Tracker(run_id, RunProgress.model_validate(run.progress))
        # End the read transaction: the connection goes back to the pool while the model works
        # (minutes); the loaded objects stay usable and their changes are saved by the last commit.
        await session.commit()

        if tracker.has(MODEL_STEP):
            await _wake_model(tracker)
        docs_by_id = {doc.id: doc for doc in definition.documents}
        durations = await asyncio.gather(
            *(
                _extract_document(run_doc, doc, tracker)
                for run_doc in run.documents
                if (doc := docs_by_id.get(run_doc.document_id)) and doc.wants_extraction
            )
        )
        run.extraction_ms = sum(durations)

        await tracker.start(RULES_STEP)
        started = time.perf_counter()
        results = evaluate_rules(
            definition.rules,
            [
                (field.key, field.value, doc.document_type, field.type)
                for doc in run.documents
                for field in doc.fields
            ],
            doc_types_by_id={doc.id: doc.document_type for doc in definition.documents},
        )
        run.validation_ms = int((time.perf_counter() - started) * 1000)
        await tracker.finish(RULES_STEP)
        await tracker.start(FINALIZE_STEP)

        _flag_fields(run.documents, results)
        session.add_all(_rule_row(run_id, i, result) for i, result in enumerate(results))
        run.rules_total = len(results)
        run.rules_failed = sum(r.status == "failed" for r in results)
        run.rules_passed = sum(r.status == "passed" for r in results)
        run.fields_extracted = sum(
            field.value is not None for doc in run.documents for field in doc.fields
        )
        run.progress = tracker.complete()
        outcome = run_outcome(
            results,
            extraction_complete=all(
                doc.extraction and not doc.extraction.get("error") for doc in run.documents
            )
            and (run.fields_extracted > 0 or not any(doc.fields for doc in run.documents)),
        )
        if not await move_run(
            session, run_id, "done", outcome=outcome, finished_at=datetime.now(UTC)
        ):
            # Failed meanwhile (Hatchet's timeout, or stopped): a final state is never overwritten.
            await session.rollback()
            log.warning("run_finished_elsewhere")
            return
        await credits.settle_done(
            session, run_id, pages=_pages_sent(run.documents), model_ms=run.extraction_ms
        )
        await session.commit()
    log.info("run_done", outcome=outcome, rules_failed=run.rules_failed)


async def _wake_model(tracker: Tracker) -> None:
    """The model step: the server answers at once, or it was asleep and this waits for it."""
    await tracker.start(MODEL_STEP)
    started = time.perf_counter()
    asleep = await client.wake(lambda: tracker.update(MODEL_STEP, cold_start=True))
    duration_ms = int((time.perf_counter() - started) * 1000)
    log.info("model_ready", cold_start=asleep, ms=duration_ms)
    await tracker.finish(MODEL_STEP, cold_start=asleep, duration_ms=duration_ms)


def _pages_sent(documents: list[RunDocument]) -> int:
    return sum(
        ExtractionMeta.model_validate(doc.extraction).pages_sent
        for doc in documents
        if doc.extraction
    )


# Documents read and rendered at once in this process, all runs together: a document's file and
# its page images are in memory from its download to the model's answer, so this bounds a
# worker's memory, not only the model's requests (AUDIT_INFERENCE_CONCURRENCY).
_documents: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = {}


def _document_slots() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    if loop not in _documents:
        _documents.clear()  # a new event loop (tests): the old semaphore belongs to the old one
        _documents[loop] = asyncio.Semaphore(get_settings().inference_concurrency)
    return _documents[loop]


async def _extract_document(run_doc: RunDocument, doc: DocumentDef, tracker: Tracker) -> int:
    """Extract one uploaded document into its fields (one per schema leaf); its duration in ms."""
    async with _document_slots():
        return await _extract_one(run_doc, doc, tracker)


async def _extract_one(run_doc: RunDocument, doc: DocumentDef, tracker: Tracker) -> int:
    step_id = extract_step(doc.id)
    await tracker.start(step_id)
    try:
        data = await get_store().get(run_doc.storage_key)
        values, meta = await extract(doc, data, run_doc.mime_type)
    except Exception as error:
        log.exception("document_extraction_failed", document_id=doc.id)
        # Pages that reached the model are paid for even when its answer never came.
        sent = error.pages_sent if isinstance(error, ModelRequestError) else 0
        run_doc.extraction = ExtractionMeta(error=EXTRACTION_FAILED, pages_sent=sent).model_dump()
        await tracker.finish(step_id, failed=True)
        return 0
    run_doc.extraction = meta.model_dump()
    run_doc.fields = [
        ExtractedField(
            id=new_id("fld"),
            position=position,
            key=value.key,
            description=value.description,
            type=value.type,
            value=value.value,
        )
        for position, value in enumerate(values)
    ]
    await tracker.finish(
        step_id,
        duration_ms=meta.extraction_ms,
        fields_extracted=meta.fields_extracted,
        failed=meta.error is not None,
    )
    return meta.extraction_ms


def run_outcome(results: list[RuleOutcome], *, extraction_complete: bool) -> Outcome:
    """Failed when a rejecting rule fails; needs review when another rule fails, or when the
    model read nothing or a document could not be read: a run is never green on no evidence."""
    failed = [r for r in results if r.status == "failed"]
    if any(r.rule.severity == "reject" for r in failed):
        return "failed"
    return "warning" if failed or not extraction_complete else "passed"


def _flag_fields(documents: list[RunDocument], results: list[RuleOutcome]) -> None:
    """Flag the fields a failed rule read: by bare name or ``<document type>.<field>``."""
    failed = {field_key(f) for r in results if r.status == "failed" for f in r.affected_fields}
    for doc in documents:
        for field in doc.fields:
            names = {field_key(field.key), field_key(f"{doc.document_type}.{field.key}")}
            field.flagged = bool(names & failed)


def _rule_row(run_id: str, position: int, result: RuleOutcome) -> RuleResult:
    return RuleResult(
        id=new_id("rr"),
        run_id=run_id,
        position=position,
        rule_id=result.rule.id,
        name=result.rule.name or result.rule.id,
        scope=result.rule.scope,
        severity=result.rule.severity,
        status=result.status,
        expression=result.expression,
        detail=result.detail,
        affected_fields=result.affected_fields,
    )
