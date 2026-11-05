"""Process one run on a worker: claim, extract each document, check the rules, save the report.

A document whose extraction fails is logged and left without fields (its rules are skipped);
any other error, or running past AUDIT_RUN_TIMEOUT_MINUTES, fails the run.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from repody.app.progress import FINALIZE_STEP, RULES_STEP, Tracker, extract_step, publish
from repody.app.runs import fail_run
from repody.extraction.pipeline import extract
from repody.infra import db
from repody.infra.models import ExtractedField, RuleResult, Run, RunDocument, new_id
from repody.infra.storage import get_store
from repody.rules.evaluate import RuleOutcome, evaluate_rules
from repody.rules.values import field_key
from repody.schemas.run import RunProgress
from repody.schemas.workflow import WorkflowDefinition
from repody.settings import get_settings

log = structlog.get_logger(__name__)

FAILURE_MESSAGE = "The run failed while processing. The worker logs have the details."


async def process_run(run_id: str) -> None:
    minutes = get_settings().run_timeout_minutes
    structlog.contextvars.bind_contextvars(run_id=run_id)
    try:
        async with asyncio.timeout(minutes * 60):
            await _process(run_id)
    except TimeoutError:
        await fail_run(run_id, f"The run took longer than {minutes} minutes.", only_if="running")
    except Exception:
        log.exception("run_processing_failed")
        await fail_run(run_id, FAILURE_MESSAGE)
    finally:
        structlog.contextvars.unbind_contextvars("run_id")


async def _claim(run_id: str) -> bool:
    async with db.session_factory() as session:
        claimed = await session.execute(
            update(Run)
            .where(Run.id == run_id, Run.status == "queued")
            .values(status="running", started_at=datetime.now(UTC))
            .returning(Run.id)
        )
        await session.commit()
        return claimed.scalar_one_or_none() is not None


async def _process(run_id: str) -> None:
    if not await _claim(run_id):
        log.info("run_already_claimed")
        return
    async with db.session_factory() as session:
        run = await session.scalar(
            select(Run)
            .where(Run.id == run_id)
            .options(selectinload(Run.documents).selectinload(RunDocument.fields))
        )
        assert run is not None
        definition = WorkflowDefinition.model_validate(run.definition)
        tracker = Tracker(run_id, RunProgress.model_validate(run.progress))
        # End the read transaction: the connection goes back to the pool while the model works
        # (minutes); the loaded objects stay usable and their changes are saved by the last commit.
        await session.commit()

        fields = await _extract_documents(run, definition, tracker)
        await tracker.start(RULES_STEP, "Checking the rules…")
        started = time.perf_counter()
        results = evaluate_rules(
            definition.rules,
            [(f.key, f.value, doc_type, f.type) for f, doc_type in fields],
            doc_types_by_id={doc.id: doc.document_type for doc in definition.documents},
            multi_document=sum(bool(doc.schema_fields) for doc in definition.documents) > 1,
        )
        run.validation_ms = int((time.perf_counter() - started) * 1000)
        await tracker.start(FINALIZE_STEP, "Saving the audit report…")

        _flag_fields(fields, results)
        session.add_all(_rule_row(run_id, i, result) for i, result in enumerate(results))
        run.status, run.outcome, run.finished_at = "done", _outcome(results), datetime.now(UTC)
        run.rules_total = len(results)
        run.rules_failed = sum(r.status == "failed" for r in results)
        run.rules_passed = sum(r.status == "passed" for r in results)
        run.fields_extracted = sum(f.value is not None for f, _ in fields)
        run.progress = tracker.finish()
        await session.commit()
    await publish(run_id, {"terminal": True, "status": "done"})
    log.info("run_done", outcome=run.outcome, rules_failed=run.rules_failed)


async def _extract_documents(
    run: Run, definition: WorkflowDefinition, tracker: Tracker
) -> list[tuple[ExtractedField, str]]:
    """Extract every uploaded document; ``(saved field, document type)`` for each leaf."""
    docs_by_id = {doc.id: doc for doc in definition.documents}
    saved: list[tuple[ExtractedField, str]] = []
    for run_doc in run.documents:
        doc = docs_by_id.get(run_doc.document_id)
        if doc is None or not doc.wants_extraction:
            continue
        step_id = extract_step(doc.id)
        await tracker.start(step_id, f"Extracting {doc.document_type or 'document'}…")
        try:
            data = await get_store().get(run_doc.storage_key)
            values, meta = await extract(doc, data, run_doc.mime_type)
        except Exception:
            log.exception("document_extraction_failed", document_id=doc.id)
            continue
        run_doc.extraction = meta.model_dump()
        run.extraction_ms += meta.extraction_ms
        for position, value in enumerate(values):
            field = ExtractedField(
                id=new_id("fld"),
                position=position,
                key=value.key,
                description=value.description,
                type=value.type,
                value=value.value,
            )
            run_doc.fields.append(field)
            saved.append((field, run_doc.document_type))
        if step := tracker.step(step_id):
            step.duration_ms, step.cache_hit = meta.extraction_ms, meta.cache_hit
            step.detail = f"{meta.fields_extracted} field(s) in {meta.extraction_ms} ms"
    return saved


def _outcome(results: list[RuleOutcome]) -> str:
    failed = [r for r in results if r.status == "failed"]
    if any(r.rule.severity == "reject" for r in failed):
        return "failed"
    return "warning" if failed else "passed"


def _flag_fields(fields: list[tuple[ExtractedField, str]], results: list[RuleOutcome]) -> None:
    """Flag the fields a failed rule read: by bare name or ``<document type>.<field>``."""
    failed = {field_key(f) for r in results if r.status == "failed" for f in r.affected_fields}
    for field, doc_type in fields:
        field.flagged = bool({field_key(field.key), field_key(f"{doc_type}.{field.key}")} & failed)


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
