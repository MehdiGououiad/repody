"""IDP agent run — load claimed Run → compose_idp → persist/complete."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.agents.idp.adapters.mapping import build_idp_input, stored_document
from audit_workbench.agents.idp.adapters.persist import (
    ensure_run_document,
    extraction_step_detail,
    persist_extraction,
    persist_idp_outcome,
)
from audit_workbench.agents.idp.adapters.validate import validate_extraction
from audit_workbench.agents.idp.adapters.extract import extract_one
from audit_workbench.agents.idp.compose import ExtractionJob, compose_idp
from audit_workbench.agents.idp.contracts import (
    DocumentExtraction,
    DocumentSpec,
    ExtractionOutput,
    IdpInput,
    IdpOutcome,
    StoredDocument,
    ValidationOutput,
)
from audit_workbench.infra.db.models import Run, RunDocument
from audit_workbench.extraction.modes import (
    DEFAULT_READ_PATH_ID,
    ValidationMode,
    is_serverless_inference,
    parse_read_path,
    read_path_label,
    resolve_run_validation_mode,
    validation_mode_label,
)
from audit_workbench.extraction.schema import icl_examples_from_document
from audit_workbench.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus
from audit_workbench.runtime.contracts.result import AppError, ErrorCode, Result
from audit_workbench.rules.types import rule_kind
from audit_workbench.app.run.helpers import extract_label, progress_mode
from audit_workbench.app.run.progress import (
    build_run_progress_plan,
    mark_step_done,
    set_run_progress,
    step_index_for,
)
from audit_workbench.app.run.snapshot import (
    SnapshotDocument,
    resolve_run_documents,
    resolve_run_rules,
    resolve_workflow_display_name,
)
from audit_workbench.infra.storage.factory import get_storage

log = structlog.get_logger()

_GPU_COLD_START_DETAIL = "Serverless GPU may need 1-2 min to start on the first request after idle"


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
    """Ports for compose_idp — short-lived DB sessions around extract HTTP."""

    run_id: str
    progress_steps: list[dict]
    files: set[str]
    snap_by_id: dict[str, SnapshotDocument]
    validation_mode: ValidationMode
    rules_payload: list[dict]
    labels: dict[str, str]
    multi_document: bool
    fetch_bytes: Any
    step_index: int = 1
    fields_extracted: int = 0
    extraction_total_ms: int = 0
    validation_ms: int = 0
    _validation_started: float | None = field(default=None, repr=False)

    async def extract_one(
        self,
        spec: DocumentSpec,
        stored: StoredDocument,
        blob: bytes,
    ) -> Result[DocumentExtraction]:
        # No DB session held during VLM/HTTP extract.
        snap = self.snap_by_id.get(spec.id)
        icl = icl_examples_from_document(snap) if snap is not None else []
        return await extract_one(
            spec,
            stored,
            blob,
            validation_mode=self.validation_mode,
            icl_examples=icl or None,
        )

    def _activate(self, step_id: str) -> int:
        """Point progress at ``step_id`` (by plan index). Falls back to current index."""
        found = step_index_for(self.progress_steps, step_id)
        if found is not None:
            self.step_index = found
        return self.step_index

    def _first_rule_step_id(self) -> str | None:
        for step in self.progress_steps:
            sid = str(step.get("id") or "")
            if sid.startswith("rule-"):
                return sid
        return None

    async def on_extract_start(self, job: ExtractionJob, index: int, total: int) -> None:
        from audit_workbench.infra.db.base import async_session_factory

        snap = self.snap_by_id.get(job.document_id)
        has_file = job.document_id in self.files
        prog_mode = progress_mode(snap or job.spec, has_file=has_file)
        step_id = f"extract-{job.document_id}"
        self._activate(step_id)

        async with async_session_factory() as session:
            await ensure_run_document(
                session,
                run_id=self.run_id,
                document_id=job.document_id,
                document_type=job.spec.label,
                existing={},
            )
            await session.commit()

        read_label = read_path_label(
            parse_read_path(job.spec.extraction_mode or DEFAULT_READ_PATH_ID).id
        )
        detail = read_label
        if is_serverless_inference() and prog_mode == "document_model":
            detail = f"{detail} · {_GPU_COLD_START_DETAIL}"
            for step in self.progress_steps:
                if step.get("id") == step_id:
                    step["gpuColdStartHint"] = True
                    break

        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            extract_label(job.spec.label, mode=prog_mode, detail=detail),
            force=(index == 0 or index == total - 1),
        )

    async def on_extract_done(
        self, job: ExtractionJob, result: Result[DocumentExtraction]
    ) -> None:
        if not result.is_ok or result.value is None:
            return
        from audit_workbench.infra.db.base import async_session_factory

        mapped = result.value
        async with async_session_factory() as session:
            run_doc = await ensure_run_document(
                session,
                run_id=self.run_id,
                document_id=job.document_id,
                document_type=job.spec.label,
                existing={},
            )
            n = await persist_extraction(session, run_doc=run_doc, extraction=mapped)
            await session.commit()
        self.fields_extracted += n
        self.extraction_total_ms += mapped.meta.extraction_ms
        step_id = f"extract-{job.document_id}"
        mark_step_done(
            self.progress_steps,
            step_id,
            duration_ms=mapped.meta.extraction_ms,
            detail=extraction_step_detail(mapped),
            cache_hit=mapped.meta.cache_hit,
        )
        # Keep currentIndex on this extract step until validation activates the next one.
        self._activate(step_id)
        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            extract_label(job.spec.label, mode="document_model"),
            force=True,
        )

    async def on_rule_start(self, rule: dict) -> None:
        name = rule.get("name") or "Rule"
        rule_id = rule.get("id") or "rule"
        step_id = f"rule-{rule_id}"
        kind = rule_kind(rule)
        for step in self.progress_steps:
            if step.get("id") == step_id:
                step["detail"] = (
                    "Evaluating LLM rule against extracted fields"
                    if kind == "llm"
                    else "Logic expression on extracted fields"
                )
                break
        self._activate(step_id)
        label = f"LLM rule · {name}…" if kind == "llm" else f"Validate · {name}…"
        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            label,
            force=True,
        )

    async def validate(self, extraction: ExtractionOutput) -> ValidationOutput:
        if extraction.by_document and self.rules_payload:
            self._validation_started = datetime.now(UTC).timestamp()
            first_rule = self._first_rule_step_id()
            if first_rule:
                self._activate(first_rule)
            await set_run_progress(
                None,
                self.run_id,
                self.progress_steps,
                self.step_index,
                f"Validating rules ({validation_mode_label(self.validation_mode)})…",
                force=True,
            )
        out = await validate_extraction(
            extraction,
            rules=self.rules_payload,
            labels=self.labels,
            multi_document=self.multi_document,
            validation_mode=self.validation_mode,
            on_rule_start=self.on_rule_start,
        )
        if self._validation_started is not None:
            self.validation_ms = int(
                (datetime.now(UTC).timestamp() - self._validation_started) * 1000
            )
        for row in out.rule_results:
            mark_step_done(
                self.progress_steps,
                f"rule-{row.rule_id}",
                detail=f"Status: {row.status} — {row.detail or 'OK'}",
            )
        return out

    async def mark_saving(self) -> None:
        self._activate("finalize")
        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            "Saving audit report…",
            force=True,
        )


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
    *,
    complete: bool = True,
) -> Result[AgentOutcome]:
    """Load → compose (extract+validate) → persist; complete when ``complete`` is True."""
    run_id = run.id
    inp = _load_idp_input(run)
    snapshot_docs = resolve_run_documents(run)
    snap_by_id = {d.id: d for d in snapshot_docs}
    rules_payload = resolve_run_rules(run, run.workflow)
    progress_steps = _initial_progress_steps(run)
    files = _docs_with_files(run)
    validation_mode = resolve_run_validation_mode(rules_payload)
    labels = {d.id: d.label for d in inp.workflow.documents}
    multi_document = sum(1 for d in inp.workflow.documents if d.schema_fields) > 1

    await set_run_progress(session, run_id, progress_steps, 1, "Starting audit run…", force=True)
    await session.commit()

    storage = get_storage()

    async def fetch_bytes(key: str) -> bytes:
        return await storage.get_bytes(key)

    ports = IdpRunPorts(
        run_id=run_id,
        progress_steps=progress_steps,
        files=files,
        snap_by_id=snap_by_id,
        validation_mode=validation_mode,
        rules_payload=rules_payload,
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
    await ports.mark_saving()

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
        complete=complete,
    )
    if not overall_r.is_ok:
        err = overall_r.error or AppError(code=ErrorCode.INFRA, message="persist_idp_outcome failed")
        return Result.fail(err)

    overall = overall_r.unwrap()
    log.info(
        "run_validation_completed",
        event_domain="audit_run",
        run_id=run_id,
        overall_status=overall,
        complete=complete,
        rules_total=len(idp_outcome.validation.rule_results),
        rules_failed=sum(
            1 for row in idp_outcome.validation.rule_results if row.status in ("failed", "error")
        ),
    )
    return Result.ok(wrap_idp_outcome(idp_outcome))
