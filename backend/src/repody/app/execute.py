"""Process one run on a worker: claim, extract the documents, check the rules, save the report.

Documents are extracted concurrently (bounded by AUDIT_INFERENCE_CONCURRENCY). A document
whose extraction fails keeps its error on the report and has no values (its rules are
skipped); any other error, or running past AUDIT_RUN_TIMEOUT_MINUTES, fails the run.
"""

import asyncio
import time
from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import selectinload

from repody.app.lifecycle import fail_run, move_run
from repody.app.progress import FINALIZE_STEP, MODEL_STEP, RULES_STEP, Tracker, extract_step
from repody.extraction import client
from repody.extraction.pipeline import extract
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
    """The ``process_run`` task: run it to the end, or mark it failed."""
    minutes = get_settings().run_timeout_minutes
    with structlog.contextvars.bound_contextvars(run_id=run_id):
        deadline = asyncio.timeout(minutes * 60)
        try:
            async with deadline:
                await _process(run_id)
        except TimeoutError:
            if not deadline.expired():  # a timeout of its own (database, network), not ours
                log.exception("run_processing_failed")
                await fail_run(run_id, FAILURE_MESSAGE)
                return
            message = f"The run took longer than {minutes} minutes."
            await fail_run(run_id, message, only_if="running")
        except Exception:
            log.exception("run_processing_failed")
            await fail_run(run_id, FAILURE_MESSAGE)


async def _claim(run_id: str) -> bool:
    async with db.session_factory() as session:
        claimed = await move_run(session, run_id, "running", started_at=datetime.now(UTC))
        await session.commit()
        return claimed


async def _process(run_id: str) -> None:
    if not await _claim(run_id):
        log.info("run_already_claimed")
        return
    async with db.session_factory() as session:
        run = await session.get_one(
            Run, run_id, options=[selectinload(Run.documents).selectinload(RunDocument.fields)]
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
        outcome = _outcome(results)
        if not await move_run(
            session, run_id, "done", outcome=outcome, finished_at=datetime.now(UTC)
        ):
            # Failed meanwhile (timeout or maintenance): a final state is never overwritten.
            await session.rollback()
            log.warning("run_finished_elsewhere")
            return
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


async def _extract_document(run_doc: RunDocument, doc: DocumentDef, tracker: Tracker) -> int:
    """Extract one uploaded document into its fields (one per schema leaf); its duration in ms."""
    step_id = extract_step(doc.id)
    await tracker.start(step_id)
    try:
        data = await get_store().get(run_doc.storage_key)
        values, meta = await extract(doc, data, run_doc.mime_type)
    except Exception:
        log.exception("document_extraction_failed", document_id=doc.id)
        run_doc.extraction = ExtractionMeta(error=EXTRACTION_FAILED).model_dump()
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
        cache_hit=meta.cache_hit,
        fields_extracted=meta.fields_extracted,
        failed=meta.error is not None,
    )
    return meta.extraction_ms


def _outcome(results: list[RuleOutcome]) -> Outcome:
    failed = [r for r in results if r.status == "failed"]
    if any(r.rule.severity == "reject" for r in failed):
        return "failed"
    return "warning" if failed else "passed"


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
