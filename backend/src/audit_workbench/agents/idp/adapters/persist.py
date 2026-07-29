"""Persist IdpOutcome pieces and optionally complete the platform run."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.agents.idp.contracts import DocumentExtraction, ValidationOutput
from audit_workbench.infra.db.models import (
    ExtractedField,
    RuleResult,
    Run,
    RunDocument,
)
from audit_workbench.extraction.modes import completed_extraction_detail, validation_mode_label
from audit_workbench.runtime.agent_metadata import PendingCompletion, store_pending_completion
from audit_workbench.runtime.contracts.result import AppError, ErrorCode, Result
from audit_workbench.runtime.run.ids import new_id
from audit_workbench.app.mappers import duration_ms_between
from audit_workbench.app.run.commands import (
    CompleteRunRequest,
    complete_run,
    publish_run_domain_events,
)
from audit_workbench.app.run.helpers import meta_to_dict
from audit_workbench.app.run.lifecycle import RunCompletionOutcome
from audit_workbench.app.run.persistence import (
    bind_commit,
    bind_load,
    bind_save,
)
from audit_workbench.app.run.progress import progress_snapshot
from audit_workbench.settings import get_settings


def extraction_meta_to_dict(doc: DocumentExtraction) -> dict:
    """Serialize pipeline meta for run_documents.extraction_meta (API wire shape)."""
    fields_n = sum(1 for f in doc.fields if f.extracted)
    meta = replace(
        doc.meta,
        fields_extracted=fields_n,
        markdown_text=doc.meta.markdown_text if doc.meta.markdown_text is not None else doc.markdown_text,
        raw_text=doc.meta.raw_text if doc.meta.raw_text is not None else doc.raw_text,
    )
    return meta_to_dict(meta)


def extraction_step_detail(doc: DocumentExtraction) -> str:
    return completed_extraction_detail(doc.meta)


async def ensure_run_document(
    session: AsyncSession,
    *,
    run_id: str,
    document_id: str,
    document_type: str,
    existing: dict[str, RunDocument],
) -> RunDocument:
    run_doc = existing.get(document_id)
    if run_doc is not None:
        if not run_doc.document_type:
            run_doc.document_type = document_type
        return run_doc
    found = (
        await session.execute(
            select(RunDocument).where(
                RunDocument.run_id == run_id,
                RunDocument.document_id == document_id,
            )
        )
    ).scalar_one_or_none()
    if found is not None:
        if not found.document_type:
            found.document_type = document_type
        existing[document_id] = found
        return found
    run_doc = RunDocument(
        id=new_id("rdoc"),
        run_id=run_id,
        document_id=document_id,
        document_type=document_type,
    )
    session.add(run_doc)
    await session.flush()
    existing[document_id] = run_doc
    return run_doc


async def persist_extraction(
    session: AsyncSession,
    *,
    run_doc: RunDocument,
    extraction: DocumentExtraction,
) -> int:
    fields_n = 0
    run_doc.extraction_meta = extraction_meta_to_dict(extraction)
    for field in extraction.fields:
        if field.extracted:
            fields_n += 1
        session.add(
            ExtractedField(
                id=new_id("fld"),
                run_document_id=run_doc.id,
                key=field.key,
                description=field.description,
                value=field.value,
                type=field.field_type,
                confidence=field.confidence,
                extracted=field.extracted,
                flagged=False,
            )
        )
    return fields_n


def _build_completion_outcome(
    *,
    validation: ValidationOutput,
    progress_steps: list[dict],
    fields_extracted: int,
    extraction_total_ms: int,
    validation_ms: int,
    validation_mode: str,
    started_at: datetime | None,
    finished_at: datetime,
) -> RunCompletionOutcome:
    duration_ms = duration_ms_between(started_at, finished_at)
    progress = None
    if progress_steps:
        progress = progress_snapshot(progress_steps, len(progress_steps) - 1, "Complete")
        for step in progress["steps"]:
            step["status"] = "done"
    return RunCompletionOutcome(
        overall_status=validation.overall_status,
        summary_total=len(validation.rule_results),
        summary_passed=validation.summary_passed,
        summary_failed=validation.summary_failed,
        fields_extracted=fields_extracted,
        run_metadata={
            "startedAt": started_at.isoformat() if started_at else None,
            "finishedAt": finished_at.isoformat(),
            "durationMs": duration_ms,
            "extractionMs": extraction_total_ms,
            "validationMs": validation_ms,
            "validationMode": validation_mode,
            "validationLabel": validation_mode_label(validation_mode),
            "llmModel": get_settings().validation_model,
        },
        progress=progress,
    )


async def persist_idp_outcome(
    session: AsyncSession,
    *,
    run_id: str,
    validation: ValidationOutput,
    progress_steps: list[dict],
    fields_extracted: int,
    extraction_total_ms: int,
    validation_ms: int,
    validation_mode: str,
    started_at: datetime | None,
    complete: bool = True,
) -> Result[str]:
    """Persist fields/rules. When ``complete`` is True, terminalize the run."""
    run = (
        await session.execute(
            select(Run)
            .where(Run.id == run_id)
            .options(selectinload(Run.documents).selectinload(RunDocument.fields))
        )
    ).scalar_one()

    rule_results = validation.rule_results
    failed_field_keys: set[str] = set()
    for row in rule_results:
        if row.status in ("failed", "error"):
            failed_field_keys.update(row.affected_fields)
            failed_field_keys.update(k.lower() for k in row.affected_fields)

    for run_doc in run.documents:
        for fld in run_doc.fields:
            norm = fld.key.strip().lower().replace(" ", "_")
            fld.flagged = fld.key in failed_field_keys or norm in failed_field_keys

    await session.execute(delete(RuleResult).where(RuleResult.run_id == run_id))
    for row in rule_results:
        session.add(
            RuleResult(
                id=new_id("rr"),
                run_id=run.id,
                rule_id=row.rule_id,
                name=row.name,
                kind=row.kind,
                scope=row.scope,
                status=row.status,
                severity=row.severity,
                expression=row.expression,
                affected_fields=list(row.affected_fields),
                detail=row.detail,
                expected_value=row.expected_value,
                actual_value=row.actual_value,
            )
        )

    finished_at = datetime.now(UTC)
    completion = _build_completion_outcome(
        validation=validation,
        progress_steps=progress_steps,
        fields_extracted=fields_extracted,
        extraction_total_ms=extraction_total_ms,
        validation_ms=validation_ms,
        validation_mode=validation_mode,
        started_at=started_at,
        finished_at=finished_at,
    )

    if not complete:
        store_pending_completion(
            run,
            PendingCompletion(
                overall_status=completion.overall_status,
                summary_total=completion.summary_total,
                summary_passed=completion.summary_passed,
                summary_failed=completion.summary_failed,
                fields_extracted=completion.fields_extracted,
                run_metadata=completion.run_metadata,
                progress=completion.progress,
            ),
        )
        if completion.progress is not None:
            run.progress = completion.progress
        await session.commit()
        return Result.ok(validation.overall_status)

    completed = await complete_run(
        CompleteRunRequest(run_id=run_id, outcome=completion),
        load=bind_load(session),
        save=bind_save(session),
        commit=bind_commit(session),
        publish=publish_run_domain_events,
        now=finished_at,
    )
    if not completed.is_ok:
        err = completed.error or AppError(code=ErrorCode.INFRA, message="complete_run failed")
        return Result.fail(err)
    return Result.ok(validation.overall_status)
