"""Run create / poll application — session orchestration (services layer)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.app.mappers import run_to_audit_detail
from repody.app.queue.progress import (
    enrich_progress_for_poll,
    init_queued_progress_with_position,
)
from repody.app.run.snapshot import (
    build_run_snapshot,
    resolve_workflow_display_name,
)
from repody.app.workflow.repository import load_workflow
from repody.infra.db.models import Run, RunDocument, RunStatus
from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.runtime.run.contracts import FileBinding
from repody.runtime.run.ids import document_row_id, new_run_id
from repody.schemas.run import RunAuditDetail
from repody.schemas.workflow import (
    DocumentDefSchema,
    RunPollResponse,
    RunPollStatus,
    RunProgressSchema,
    WorkflowRuleSchema,
)


def _snapshot_from_payload(
    *,
    documents: list[DocumentDefSchema] | None = None,
    rules: list[WorkflowRuleSchema] | None = None,
    workflow_name: str | None = None,
) -> dict | None:
    doc_rows = [doc.model_dump(by_alias=False) for doc in documents] if documents else None
    rule_rows = [rule.model_dump(by_alias=False) for rule in rules] if rules else None
    return build_run_snapshot(
        documents=doc_rows,
        rules=rule_rows,
        workflow_name=workflow_name,
    )


async def create_run(
    session: AsyncSession,
    workflow_id: str,
    *,
    source: str = "test",
    file_bindings: list[FileBinding] | None = None,
    snapshot_documents: list[DocumentDefSchema] | None = None,
    snapshot_rules: list[WorkflowRuleSchema] | None = None,
    snapshot_workflow_name: str | None = None,
    worker_pool: str | None = None,
) -> Result[Run]:
    wf = await load_workflow(session, workflow_id)
    if not wf:
        return Result.fail(AppError(code=ErrorCode.NOT_FOUND, message="Workflow not found"))

    snapshot = _snapshot_from_payload(
        documents=snapshot_documents,
        rules=snapshot_rules,
        workflow_name=snapshot_workflow_name,
    )

    run = Run(
        id=new_run_id(source),
        workflow_id=workflow_id,
        source=source,
        status=RunStatus.queued.value,
        run_snapshot=snapshot,
        worker_pool=worker_pool,
    )
    session.add(run)
    await session.flush()

    for binding in file_bindings or []:
        session.add(
            RunDocument(
                id=document_row_id(),
                run_id=run.id,
                document_id=binding.document_id,
                document_type="",
                storage_key=binding.storage_key,
                mime_type=binding.mime_type,
                file_name=binding.file_name,
            )
        )
    await session.flush()

    await init_queued_progress_with_position(session, run.id)
    await session.flush()

    return Result.ok(run)


async def get_run_detail(session: AsyncSession, run_id: str) -> RunAuditDetail | None:
    result = await session.execute(
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.documents).selectinload(RunDocument.fields),
            selectinload(Run.rule_results),
            selectinload(Run.workflow),
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        return None
    name = resolve_workflow_display_name(run, run.workflow) if run.workflow else "Workflow"
    return run_to_audit_detail(run, name)


def progress_from_run(run: Run) -> RunProgressSchema | None:
    if not run.progress:
        return None
    return RunProgressSchema.model_validate(run.progress)


async def poll_run_status(session: AsyncSession, run_id: str) -> RunPollStatus:
    run = await session.get(Run, run_id)
    if not run:
        return RunPollStatus(status="failed", error="Run not found", progress=None)
    progress_dict = await enrich_progress_for_poll(session, run)
    progress = (
        RunProgressSchema.model_validate(progress_dict) if progress_dict else progress_from_run(run)
    )
    if run.status == RunStatus.failed.value:
        return RunPollStatus(status="failed", error=run.error or "Run failed", progress=progress)
    return RunPollStatus(status=run.status, error=None, progress=progress)


async def poll_run(session: AsyncSession, run_id: str) -> RunPollResponse:
    body = await poll_run_status(session, run_id)
    progress = body.progress
    status = body.status
    if status == "done":
        detail = await get_run_detail(session, run_id)
        return RunPollResponse(status="done", result=detail, error=None, progress=progress)
    if status == "failed":
        return RunPollResponse(
            status="failed",
            result=None,
            error=body.error or "Run failed",
            progress=progress,
        )
    return RunPollResponse(status=status, result=None, error=None, progress=progress)
