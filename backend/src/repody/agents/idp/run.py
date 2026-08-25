"""IDP agent run — load claimed Run → compose_idp → persist/complete."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from repody.agents.idp.adapters.extract import extract_one
from repody.agents.idp.adapters.mapping import build_idp_input, stored_document
from repody.agents.idp.adapters.persist import (
    ensure_run_document,
    persist_extraction,
    persist_idp_outcome,
)
from repody.agents.idp.adapters.validate import validate_extraction
from repody.agents.idp.compose import ExtractionJob, compose_idp
from repody.agents.idp.contracts import (
    DocumentExtraction,
    DocumentSpec,
    ExtractionOutput,
    IdpInput,
    IdpOutcome,
    RuleSpec,
    StoredDocument,
    ValidationOutput,
)
from repody.agents.idp.progress import IdpProgressPresenter
from repody.app.run.progress import (
    build_run_progress_plan,
    mark_step_done,
    set_run_progress,
)
from repody.app.run.snapshot import (
    resolve_run_documents,
    resolve_run_rules,
    resolve_workflow_display_name,
)
from repody.extraction.modes import ValidationMode, resolve_run_validation_mode
from repody.extraction.schema import icl_examples_from_document
from repody.infra.db.base import async_session_factory
from repody.infra.db.models import Run
from repody.infra.storage.factory import get_storage
from repody.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus
from repody.runtime.contracts.result import AppError, ErrorCode, Result

log = structlog.get_logger()


def agent_status_from_idp(outcome: IdpOutcome) -> AgentStatus:
    if outcome.errors:
        return AgentStatus.PARTIAL
    if outcome.validation.overall_status == "passed":
        return AgentStatus.PASSED
    if outcome.validation.overall_status == "warning":
        return AgentStatus.PARTIAL
    return AgentStatus.FAILED


def wrap_idp_outcome(outcome: IdpOutcome) -> AgentOutcome:
    return AgentOutcome(
        agent=AgentId.IDP,
        status=agent_status_from_idp(outcome),
        payload=outcome,
        errors=outcome.errors,
    )


@dataclass
class IdpRunPorts:
    """Thin extract/validate/persist adapters; progress lives on the presenter."""

    session_factory: async_sessionmaker[AsyncSession]
    progress: IdpProgressPresenter
    validation_mode: ValidationMode
    rules: tuple[RuleSpec, ...]
    labels: dict[str, str]
    multi_document: bool
    fetch_bytes: Any
    fields_extracted: int = 0
    extraction_total_ms: int = 0
    validation_ms: int = 0

    async def extract_one(
        self,
        spec: DocumentSpec,
        stored: StoredDocument,
        blob: bytes,
    ) -> Result[DocumentExtraction]:
        snap = self.progress.snap_by_id.get(spec.id)
        icl = icl_examples_from_document(snap) if snap is not None else []
        return await extract_one(
            spec,
            stored,
            blob,
            validation_mode=self.validation_mode,
            icl_examples=icl or None,
        )

    async def on_extract_start(self, job: ExtractionJob, index: int, total: int) -> None:
        async with self.session_factory() as session:
            await ensure_run_document(
                session,
                run_id=self.progress.run_id,
                document_id=job.document_id,
                document_type=job.spec.label,
                existing={},
            )
            await session.commit()
        await self.progress.on_extract_start(job, index, total)

    async def on_extract_done(self, job: ExtractionJob, result: Result[DocumentExtraction]) -> None:
        if not result.is_ok or result.value is None:
            return
        mapped = result.value
        async with self.session_factory() as session:
            run_doc = await ensure_run_document(
                session,
                run_id=self.progress.run_id,
                document_id=job.document_id,
                document_type=job.spec.label,
                existing={},
            )
            n = await persist_extraction(session, run_doc=run_doc, extraction=mapped)
            await session.commit()
        self.fields_extracted += n
        self.extraction_total_ms += mapped.meta.extraction_ms
        await self.progress.on_extract_done(job, mapped.meta)

    async def validate(self, extraction: ExtractionOutput) -> ValidationOutput:
        await self.progress.on_validation_start(
            has_rules=bool(extraction.by_document and self.rules)
        )
        out = await validate_extraction(
            extraction,
            rules=self.rules,
            labels=self.labels,
            multi_document=self.multi_document,
            validation_mode=self.validation_mode,
            on_rule_start=self.progress.on_rule_start,
        )
        self.validation_ms = self.progress.validation_elapsed_ms()
        self.progress.mark_rules_done(out.rule_results)
        return out


def _docs_with_files(run: Run) -> set[str]:
    return {rd.document_id for rd in run.documents if rd.document_id and rd.storage_key}


def _load_idp_input(run: Run) -> IdpInput:
    workflow = run.workflow
    if workflow is None:
        raise ValueError(f"Run {run.id} has no workflow")
    snapshot_docs = resolve_run_documents(run)
    rules = resolve_run_rules(run, workflow)
    stored = []
    by_id = {rd.document_id: rd for rd in run.documents if rd.document_id}
    for doc in snapshot_docs:
        rd = by_id.get(doc.id)
        if rd is None or not rd.storage_key:
            continue
        stored.append(
            stored_document(
                document_id=doc.id,
                storage_key=rd.storage_key,
                mime_type=rd.mime_type or "application/octet-stream",
                size_bytes=0,
            )
        )
    return build_idp_input(
        run_id=run.id,
        workflow_id=workflow.id,
        documents=snapshot_docs,
        rules=rules,
        stored=stored,
        workflow_name=resolve_workflow_display_name(run, workflow),
    )


def _initial_progress_steps(run: Run) -> list[dict]:
    snapshot_docs = resolve_run_documents(run)
    rules = resolve_run_rules(run, run.workflow)
    steps = build_run_progress_plan(
        workflow_docs=snapshot_docs,
        rules=rules,
        docs_with_files=_docs_with_files(run),
    )
    mark_step_done(steps, "queue", detail="Taskiq worker picked up job")
    return steps


async def execute_idp_run(
    session: AsyncSession,
    run: Run,
) -> Result[AgentOutcome]:
    """Load → compose (extract+validate) → persist and complete the platform run."""
    run_id = run.id
    inp = _load_idp_input(run)
    snapshot_docs = resolve_run_documents(run)
    snap_by_id = {d.id: d for d in snapshot_docs}
    progress_steps = _initial_progress_steps(run)
    files = _docs_with_files(run)
    validation_mode = resolve_run_validation_mode(resolve_run_rules(run, run.workflow))
    labels = {d.id: d.label for d in inp.workflow.documents}
    multi_document = sum(1 for d in inp.workflow.documents if d.schema_fields) > 1

    await set_run_progress(session, run_id, progress_steps, 1, "Starting audit run…", force=True)
    await session.commit()

    storage = get_storage()

    async def fetch_bytes(key: str) -> bytes:
        return await storage.get_bytes(key)

    progress = IdpProgressPresenter(
        run_id=run_id,
        progress_steps=progress_steps,
        files=files,
        snap_by_id=snap_by_id,
        validation_mode=validation_mode,
    )
    ports = IdpRunPorts(
        session_factory=async_session_factory,
        progress=progress,
        validation_mode=validation_mode,
        rules=inp.workflow.rules,
        labels=labels,
        multi_document=multi_document,
        fetch_bytes=fetch_bytes,
    )

    outcome_r = await compose_idp(
        inp,
        fetch_bytes=ports.fetch_bytes,
        extract_one=ports.extract_one,
        validate=ports.validate,
        on_extract_start=ports.on_extract_start,
        on_extract_done=ports.on_extract_done,
    )
    if not outcome_r.is_ok or outcome_r.value is None:
        err = outcome_r.error or AppError(code=ErrorCode.EXTRACTION, message="compose_idp failed")
        return Result.fail(err)

    idp_outcome = outcome_r.value
    await session.flush()
    await progress.mark_saving()

    overall_r = await persist_idp_outcome(
        session,
        run_id=run_id,
        validation=idp_outcome.validation,
        progress_steps=progress_steps,
        fields_extracted=ports.fields_extracted,
        extraction_total_ms=ports.extraction_total_ms,
        validation_ms=ports.validation_ms,
        validation_mode=validation_mode,
        started_at=run.started_at,
    )
    if not overall_r.is_ok:
        err = overall_r.error or AppError(
            code=ErrorCode.INFRA, message="persist_idp_outcome failed"
        )
        return Result.fail(err)

    overall = overall_r.unwrap()
    log.info(
        "run_validation_completed",
        event_domain="audit_run",
        run_id=run_id,
        overall_status=overall,
        rules_total=len(idp_outcome.validation.rule_results),
        rules_failed=sum(
            1 for row in idp_outcome.validation.rule_results if row.status in ("failed", "error")
        ),
    )
    return Result.ok(wrap_idp_outcome(idp_outcome))
