"""Process one run on a worker: claim -> extract each document -> evaluate rules -> complete.

Extraction failures are per document (logged, the document is skipped); any other error
fails the run. Progress is published over SSE as the run advances.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.app.audit.mappers import duration_ms_between
from repody.app.run.helpers import meta_to_dict, resolve_upload_mime
from repody.app.run.progress import (
    build_run_progress_plan,
    completed_extraction_detail,
    document_wants_extraction,
    mark_step_done,
    progress_snapshot,
    set_run_progress,
    step_index_for,
)
from repody.app.run.snapshot import SnapshotDocument, materialize_run_config
from repody.app.run.state import PUBLIC_RUN_FAILURE_MESSAGE, claim_run, complete_run, fail_run
from repody.extraction.pipeline import extract_document
from repody.extraction.schema import icl_examples_from_document, schema_field_spec_from_row
from repody.extraction.types import ExtractionMetadata, ExtractionResult
from repody.inference.runtime import is_serverless_inference
from repody.infra.db import base as db_base
from repody.infra.db.models import (
    Document,
    ExtractedField,
    RuleResult,
    Run,
    RunDocument,
    RunStatus,
    Workflow,
)
from repody.infra.storage.factory import get_storage
from repody.rules.runner import validate_field_rows
from repody.rules.types import RuleEvalResult
from repody.rules.value_coercion import MISSING
from repody.runtime.run.ids import new_id
from repody.settings import get_settings

log = structlog.get_logger(__name__)

_GPU_COLD_START_DETAIL = "Serverless GPU may need 1-2 min to start on the first request after idle"
_PASS = frozenset({"pass", "passed"})
_FAIL = frozenset({"fail", "failed", "error"})


async def execute_run_with_timeout(run_id: str, *, request_id: str | None = None) -> None:
    """Process one run under AUDIT_WORKER_TASK_TIMEOUT_MINUTES; a timeout fails the run."""
    minutes = get_settings().worker_task_timeout_minutes
    try:
        async with asyncio.timeout(minutes * 60):
            await process_run(run_id, request_id=request_id)
    except TimeoutError:
        await fail_run(
            run_id,
            f"Run exceeded {minutes} minute task timeout",
            expected_status=RunStatus.running.value,
        )
        raise


async def process_run(run_id: str, *, request_id: str | None = None) -> None:
    # Workers run outside the ASGI correlation-id middleware; the request id rides the task.
    log.info(
        "run_processing_started", event_domain="audit_run", run_id=run_id, request_id=request_id
    )
    async with db_base.async_session_factory() as session:
        if await claim_run(session, run_id, now=datetime.now(UTC)) is None:
            log.info("run_claim_skipped", event_domain="audit_run", run_id=run_id)
            await session.rollback()
            return
        await _clear_prior_results(session, run_id)
        await session.commit()
        try:
            await _execute(session, run_id)
        except Exception as exc:
            await session.rollback()
            await fail_run(run_id, PUBLIC_RUN_FAILURE_MESSAGE)
            log.error(
                "run_failed",
                event_domain="audit_run",
                run_id=run_id,
                error_type=type(exc).__name__,
                exc_info=exc,
            )
            raise


async def _clear_prior_results(session: AsyncSession, run_id: str) -> None:
    """A re-claimed run (retry) starts from a clean result set."""
    await session.execute(delete(RuleResult).where(RuleResult.run_id == run_id))
    run_doc_ids = select(RunDocument.id).where(RunDocument.run_id == run_id)
    await session.execute(
        delete(ExtractedField).where(ExtractedField.run_document_id.in_(run_doc_ids))
    )


async def _load_run(session: AsyncSession, run_id: str) -> Run:
    result = await session.execute(
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.documents),
            selectinload(Run.workflow)
            .selectinload(Workflow.documents)
            .selectinload(Document.schema_fields),
            selectinload(Run.workflow).selectinload(Workflow.rules),
        )
    )
    return result.scalar_one()


class _Progress:
    """The run's step plan plus which step is live; every update is published over SSE."""

    def __init__(self, run_id: str, steps: list[dict]) -> None:
        self.run_id = run_id
        self.steps = steps
        self.index = 1

    async def show(self, step_id: str | None, label: str, *, force: bool = True) -> None:
        if step_id is not None and (found := step_index_for(self.steps, step_id)) is not None:
            self.index = found
        await set_run_progress(None, self.run_id, self.steps, self.index, label, force=force)

    async def extract_start(self, doc: SnapshotDocument, index: int, total: int) -> None:
        step_id = f"extract-{doc.id}"
        label = f"Extracting {_label(doc)}…"
        if is_serverless_inference():
            label = f"{label} ({_GPU_COLD_START_DETAIL})"
            for step in self.steps:
                if step.get("id") == step_id:
                    step["gpuColdStartHint"] = True
        # Push the first and last document eagerly; the rest ride the throttle.
        await self.show(step_id, label, force=index in (0, total - 1))

    async def extract_done(self, doc: SnapshotDocument, meta: ExtractionMetadata) -> None:
        step_id = f"extract-{doc.id}"
        mark_step_done(
            self.steps,
            step_id,
            duration_ms=meta.extraction_ms,
            detail=completed_extraction_detail(meta),
            cache_hit=meta.cache_hit,
        )
        await self.show(step_id, f"Extracted {_label(doc)}")

    async def rule_start(self, rule: dict) -> None:
        step_id = f"rule-{rule.get('id') or 'rule'}"
        for step in self.steps:
            if step.get("id") == step_id:
                step["detail"] = "Logic expression on extracted fields"
        await self.show(step_id, f"Validate · {rule.get('name') or 'Rule'}…")

    def rules_done(self, results: list[RuleEvalResult]) -> None:
        for row in results:
            mark_step_done(
                self.steps, f"rule-{row.id}", detail=f"Status: {row.status} — {row.detail or 'OK'}"
            )

    def final(self) -> dict | None:
        if not self.steps:
            return None
        snapshot = progress_snapshot(self.steps, len(self.steps) - 1, "Complete")
        for step in snapshot["steps"]:
            step["status"] = "done"
        return snapshot


def _label(doc: SnapshotDocument) -> str:
    return doc.document_type or doc.id


async def _extract(doc: SnapshotDocument, run_doc: RunDocument) -> ExtractionResult:
    blob = await get_storage().get_bytes(run_doc.storage_key or "")
    schema = [
        schema_field_spec_from_row(
            name=f.name,
            description=f.description or "",
            template_type=f.template_type,
            field_config=f.field_config,
        )
        for f in doc.schema_fields
        if f.name.strip()
    ]
    return await extract_document(
        blob,
        resolve_upload_mime(run_doc.mime_type, blob),
        _label(doc),
        schema,
        extraction_instructions=doc.extraction_instructions or "",
        markdown_extraction=bool(doc.markdown_extraction),
        extraction_icl_examples=icl_examples_from_document(doc) or None,
    )


def _save_extraction(session: AsyncSession, run_doc: RunDocument, result: ExtractionResult) -> int:
    """Store meta + field rows on the run document; returns the number of extracted fields."""
    meta = result.meta
    if meta is None:
        raise ValueError("extract_document returned no metadata")
    extracted = sum(1 for f in result.fields if f.extracted)
    meta.fields_extracted = extracted
    meta.markdown_text = (
        meta.markdown_text if meta.markdown_text is not None else result.markdown_text
    )
    meta.raw_text = meta.raw_text if meta.raw_text is not None else result.raw_text
    run_doc.extraction_meta = meta_to_dict(meta)
    for field in result.fields:
        session.add(
            ExtractedField(
                id=new_id("fld"),
                run_document_id=run_doc.id,
                key=field.key,
                description=field.description or "",
                value=field.value,
                type=field.type,
                confidence=field.confidence,
                extracted=field.extracted,
                flagged=False,
            )
        )
    return extracted


def _summarize(results: list[RuleEvalResult]) -> tuple[str, int, int]:
    passed = sum(1 for r in results if r.status in _PASS)
    failed = sum(1 for r in results if r.status in _FAIL)
    if failed == 0:
        return "passed", passed, failed
    if any(r.status in _FAIL and r.severity == "reject" for r in results):
        return "failed", passed, failed
    return "warning", passed, failed


async def _execute(session: AsyncSession, run_id: str) -> None:
    run = await _load_run(session, run_id)
    started_at = run.started_at
    config = materialize_run_config(run)
    run_docs = {rd.document_id: rd for rd in run.documents if rd.document_id and rd.storage_key}
    labels = {doc.id: _label(doc) for doc in config.documents}
    multi_document = sum(1 for doc in config.documents if doc.schema_fields) > 1

    steps = build_run_progress_plan(
        workflow_docs=config.documents, rules=config.rules, docs_with_files=set(run_docs)
    )
    mark_step_done(steps, "queue", detail="Taskiq worker picked up job")
    progress = _Progress(run_id, steps)
    await progress.show(None, "Starting audit run…")

    jobs = [
        doc for doc in config.documents if doc.id in run_docs and document_wants_extraction(doc)
    ]
    rows: list[tuple[str, str, str | None]] = []
    fields_extracted = 0
    extraction_ms = 0
    for index, doc in enumerate(jobs):
        run_doc = run_docs[doc.id]
        run_doc.document_type = run_doc.document_type or _label(doc)
        await progress.extract_start(doc, index, len(jobs))
        try:
            result = await _extract(doc, run_doc)
        except Exception:
            log.exception("document_extraction_failed", run_id=run_id, document_id=doc.id)
            continue
        fields_extracted += _save_extraction(session, run_doc, result)
        extraction_ms += result.meta.extraction_ms if result.meta else 0
        run.last_activity_at = datetime.now(UTC)
        await session.commit()
        rows.extend(
            (f.key, f.value if f.extracted and f.value else MISSING, labels.get(doc.id))
            for f in result.fields
            if f.key
        )
        if result.meta is not None:
            await progress.extract_done(doc, result.meta)

    validation_started = time.perf_counter()
    if config.rules:
        first_rule = next(
            (s["id"] for s in steps if str(s.get("id", "")).startswith("rule-")), None
        )
        await progress.show(first_rule, "Validating rules…")
    results = await validate_field_rows(
        rows,
        config.rules,
        doc_types_by_id=labels,
        multi_document=multi_document,
        on_rule_start=progress.rule_start,
    )
    validation_ms = int((time.perf_counter() - validation_started) * 1000) if config.rules else 0
    progress.rules_done(results)
    await progress.show("finalize", "Saving audit report…")

    failed_keys = {
        key
        for row in results
        if row.status in _FAIL
        for raw in row.affected_fields
        for key in (raw, raw.lower())
    }
    saved_fields = await session.execute(
        select(ExtractedField)
        .join(RunDocument, ExtractedField.run_document_id == RunDocument.id)
        .where(RunDocument.run_id == run_id)
    )
    for field in saved_fields.scalars():
        field.flagged = (
            field.key in failed_keys or field.key.strip().lower().replace(" ", "_") in failed_keys
        )
    for row in results:
        session.add(
            RuleResult(
                id=new_id("rr"),
                run_id=run_id,
                rule_id=row.id,
                name=row.name,
                kind=row.kind,
                scope=row.scope,
                status=row.status,
                severity=row.severity,
                expression=row.expression or "",
                affected_fields=list(row.affected_fields),
                detail=row.detail,
                expected_value=row.expected_value,
                actual_value=row.actual_value,
            )
        )

    overall, passed, failed = _summarize(results)
    finished_at = datetime.now(UTC)
    await complete_run(
        session,
        run_id,
        overall_status=overall,
        summary_total=len(results),
        summary_passed=passed,
        summary_failed=failed,
        fields_extracted=fields_extracted,
        run_metadata={
            "startedAt": started_at.isoformat() if started_at else None,
            "finishedAt": finished_at.isoformat(),
            "durationMs": duration_ms_between(started_at, finished_at),
            "extractionMs": extraction_ms,
            "validationMs": validation_ms,
        },
        progress=progress.final(),
    )
    log.info(
        "run_validation_completed",
        event_domain="audit_run",
        run_id=run_id,
        overall_status=overall,
        rules_total=len(results),
        rules_failed=failed,
    )
