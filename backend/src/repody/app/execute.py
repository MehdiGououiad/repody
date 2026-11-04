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

from repody import db
from repody.app.progress import Tracker, publish
from repody.app.runs import fail_run
from repody.app.workflows import new_id
from repody.extraction.fields import FieldValue
from repody.extraction.pipeline import extract
from repody.models import ExtractedField, RuleResult, Run
from repody.rules.evaluate import FieldRow, RuleOutcome, evaluate_rules
from repody.rules.values import field_key
from repody.schemas.run import RunProgress
from repody.schemas.workflow import WorkflowDefinition
from repody.settings import get_settings
from repody.storage import get_store

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


def _outcome(results: list[RuleOutcome]) -> str:
    failed = [r for r in results if r.status == "failed"]
    if any(r.rule.severity == "reject" for r in failed):
        return "failed"
    return "warning" if failed else "passed"


async def _process(run_id: str) -> None:
    if not await _claim(run_id):
        log.info("run_already_claimed")
        return
    async with db.session_factory() as session:
        run = await session.scalar(
            select(Run).where(Run.id == run_id).options(selectinload(Run.documents))
        )
        assert run is not None
        definition = WorkflowDefinition.model_validate(run.definition)
        tracker = Tracker(run_id, RunProgress.model_validate(run.progress))
        docs_by_id = {doc.id: doc for doc in definition.documents}
        multi_document = sum(bool(doc.schema_fields) for doc in definition.documents) > 1

        rows: list[FieldRow] = []
        saved: list[tuple[ExtractedField, str]] = []
        extraction_ms = 0
        for run_doc in run.documents:
            doc = docs_by_id.get(run_doc.document_id)
            if doc is None or not doc.wants_extraction:
                continue
            step_id = f"extract-{doc.id}"
            await tracker.start(
                step_id, f"Extracting {doc.document_type or 'document'}…", persist=True
            )
            try:
                fields, meta = await extract(doc, await get_store().get(run_doc.storage_key))
            except Exception:
                log.exception("document_extraction_failed", document_id=doc.id)
                continue
            run_doc.extraction = meta.model_dump()
            extraction_ms += meta.extraction_ms
            for position, field in enumerate(fields):
                row = _field_row(run_doc.id, position, field)
                session.add(row)
                saved.append((row, run_doc.document_type))
            rows += [(f.key, f.value, run_doc.document_type) for f in fields]
            if step := tracker.step(step_id):
                step.duration_ms, step.cache_hit = meta.extraction_ms, meta.cache_hit
                step.detail = f"{meta.fields_extracted} field(s) in {meta.extraction_ms} ms"

        validation_started = time.perf_counter()

        async def on_rule(rule) -> None:
            await tracker.start(f"rule-{rule.id}", f"Checking {rule.name or 'rule'}…")

        results = await evaluate_rules(
            definition.rules,
            rows,
            doc_types_by_id={doc.id: doc.document_type for doc in definition.documents},
            multi_document=multi_document,
            on_rule_start=on_rule,
        )
        validation_ms = int((time.perf_counter() - validation_started) * 1000)
        await tracker.start("finalize", "Saving the audit report…")

        # Flag the fields a failed rule read: by bare name or `<document type>.<field>`.
        failed_keys = {
            field_key(f) for r in results if r.status == "failed" for f in r.affected_fields
        }
        for field, doc_type in saved:
            field.flagged = bool(
                {field_key(field.key), field_key(f"{doc_type}.{field.key}")} & failed_keys
            )
        for position, result in enumerate(results):
            session.add(_rule_row(run_id, position, result))

        run.status, run.outcome, run.finished_at = "done", _outcome(results), datetime.now(UTC)
        run.rules_total = len(results)
        run.rules_passed = sum(r.status == "passed" for r in results)
        run.rules_failed = sum(r.status == "failed" for r in results)
        run.fields_extracted = sum(1 for row, _ in saved if row.extracted)
        run.extraction_ms, run.validation_ms = extraction_ms, validation_ms
        run.progress = tracker.finish()
        await session.commit()
    await publish(run_id, {"terminal": True, "status": "done"})
    log.info("run_done", outcome=run.outcome, rules_failed=run.rules_failed)


def _field_row(run_document_id: str, position: int, field: FieldValue) -> ExtractedField:
    return ExtractedField(
        id=new_id("fld"),
        run_document_id=run_document_id,
        position=position,
        key=field.key,
        description=field.description,
        type=field.type,
        value=field.value,
        extracted=field.extracted,
    )


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
