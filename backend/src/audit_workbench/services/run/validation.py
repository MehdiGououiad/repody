"""Rule validation and run finalization phase."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import OverallStatus, RuleResult, Run, RunDocument
from audit_workbench.extraction.document_modes import ValidationMode, validation_mode_label
from audit_workbench.rules.runner import validate_extractions
from audit_workbench.rules.types import rule_kind
from audit_workbench.services.mappers import duration_ms_between
from audit_workbench.services.run.adapters.composition import (
    get_complete_run,
    run_lifecycle_store,
)
from audit_workbench.services.run.application.use_cases import CompleteRunRequest
from audit_workbench.services.run.domain.lifecycle import RunCompletionOutcome
from audit_workbench.services.run.helpers import new_id
from audit_workbench.services.run.phase_state import (
    RunPhaseState,
)
from audit_workbench.services.run.progress_persist import set_run_progress
from audit_workbench.services.run.progress_plan import mark_step_done, progress_snapshot
from audit_workbench.settings import get_settings

log = structlog.get_logger()


async def run_validation_phase(session: AsyncSession, state: RunPhaseState) -> None:
    """Validate rules and finalize run (expects extraction_results in state)."""
    run_id = state.run_id
    rules_payload = state.rules_payload
    progress_steps = state.progress_steps

    validation_started: float | None = None
    validation_ms = 0

    if state.extraction_results and rules_payload:
        state.step_index += 1
        validation_started = datetime.now(UTC).timestamp()
        val_label = validation_mode_label(state.validation_mode)
        await set_run_progress(
            session,
            run_id,
            progress_steps,
            state.step_index,
            f"Validating rules ({val_label})…",
            force=True,
        )

    async def on_rule_start(rule: dict) -> None:
        kind = rule_kind(rule)
        if kind != "llm":
            return
        state.step_index += 1
        name = rule.get("name") or "Rule"
        rule_id = rule.get("id") or "rule"
        for step in progress_steps:
            if step.get("id") == f"rule-{rule_id}":
                step["detail"] = "Evaluating LLM rule against extracted fields"
                break
        await set_run_progress(
            session, run_id, progress_steps, state.step_index, f"LLM rule · {name}…"
        )

    _field_values, rule_evals = await validate_extractions(
        extractions=state.extraction_results,
        rules=rules_payload,
        multi_document=state.multi_document,
        validation_mode=cast(ValidationMode, state.validation_mode),
        on_rule_start=on_rule_start,
        llm_model=None,
        precomputed_llm=state.precomputed_llm or None,
        doc_types_by_id={doc.id: doc.document_type for doc in state.workflow_docs},
    )

    if validation_started is not None:
        validation_ms = int((datetime.now(UTC).timestamp() - validation_started) * 1000)

    for rule in rules_payload:
        eval_rows = [
            row
            for row in rule_evals
            if row.id == (rule.get("id") or "rule")
            or row.id.startswith(f"{rule.get('id') or 'rule'}-c")
        ]
        for eval_row in eval_rows:
            mark_step_done(
                progress_steps,
                f"rule-{eval_row.id}",
                detail=f"Status: {eval_row.status} — {eval_row.detail or 'OK'}",
            )

    state.step_index += 1
    await set_run_progress(
        session, run_id, progress_steps, state.step_index, "Saving audit report…", force=True
    )

    run = (
        await session.execute(
            select(Run)
            .where(Run.id == run_id)
            .options(selectinload(Run.documents).selectinload(RunDocument.fields))
        )
    ).scalar_one()

    failed_field_keys: set[str] = set()
    for row in rule_evals:
        if row.status in ("failed", "error"):
            failed_field_keys.update(row.affected_fields)
            failed_field_keys.update(k.lower() for k in row.affected_fields)

    for run_doc in run.documents:
        for fld in run_doc.fields:
            norm = fld.key.strip().lower().replace(" ", "_")
            fld.flagged = fld.key in failed_field_keys or norm in failed_field_keys

    await session.execute(delete(RuleResult).where(RuleResult.run_id == run_id))
    for row in rule_evals:
        session.add(
            RuleResult(
                id=new_id("rr"),
                run_id=run.id,
                rule_id=row.id,
                name=row.name,
                kind=row.kind,
                scope=row.scope,
                status=row.status,
                severity=row.severity,
                expression=row.expression,
                affected_fields=row.affected_fields,
                detail=row.detail,
                expected_value=row.expected_value,
                actual_value=row.actual_value,
            )
        )

    failed_count = sum(1 for row in rule_evals if row.status in ("failed", "error"))
    has_reject = any(
        row.status in ("failed", "error") and row.severity == "reject" for row in rule_evals
    )
    if failed_count == 0:
        overall = OverallStatus.passed.value
    elif has_reject:
        overall = OverallStatus.failed.value
    else:
        overall = OverallStatus.warning.value

    finished_at = datetime.now(UTC)
    duration_ms = duration_ms_between(run.started_at, finished_at)
    started_at = run.started_at
    progress: dict | None = None
    if progress_steps:
        progress = progress_snapshot(progress_steps, len(progress_steps) - 1, "Complete")
        for step in progress["steps"]:
            step["status"] = "done"

    await get_complete_run().execute(
        CompleteRunRequest(
            run_id=run_id,
            outcome=RunCompletionOutcome(
                overall_status=overall,
                summary_total=len(rule_evals),
                summary_passed=sum(1 for row in rule_evals if row.status == "passed"),
                summary_failed=failed_count,
                fields_extracted=state.fields_extracted,
                run_metadata={
                    "startedAt": started_at.isoformat() if started_at else None,
                    "finishedAt": finished_at.isoformat(),
                    "durationMs": duration_ms,
                    "extractionMs": state.extraction_total_ms,
                    "validationMs": validation_ms,
                    "validationMode": state.validation_mode,
                    "validationLabel": validation_mode_label(state.validation_mode),
                    "llmModel": get_settings().validation_model,
                },
                progress=progress,
            ),
        ),
        store=run_lifecycle_store(session),
        now=finished_at,
    )
    log.info(
        "run_validation_completed",
        event_domain="audit_run",
        run_id=run_id,
        overall_status=overall,
        rules_total=len(rule_evals),
        rules_failed=failed_count,
    )
