"""Server-side test Run session orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.schemas.workflow import RunCreatedResponse, RunPollResponse
from audit_workbench.services.run_enqueue import EnqueueRunRequest, RunSnapshot, enqueue_run
from audit_workbench.services.run_service import FileBinding
from audit_workbench.services.run_upload_bindings import bindings_from_multipart
from audit_workbench.schemas.workflow import DocumentDefSchema, WorkflowRuleSchema


@dataclass(frozen=True)
class TestRunSessionRequest:
    workflow_id: str
    documents: list[DocumentDefSchema]
    rules: list[WorkflowRuleSchema]
    workflow_name: str | None = None
    file_bindings: list[FileBinding] | None = None


async def start_test_run_session(
    session: AsyncSession,
    req: TestRunSessionRequest,
) -> RunCreatedResponse | RunPollResponse:
    """Single interface: snapshot + optional bindings → queued test Run."""
    return await enqueue_run(
        session,
        EnqueueRunRequest(
            workflow_id=req.workflow_id,
            source="test",
            file_bindings=req.file_bindings,
            snapshot=RunSnapshot(
                documents=req.documents,
                rules=req.rules,
                workflow_name=req.workflow_name,
            ),
        ),
    )


async def start_test_run_with_uploads(
    session: AsyncSession,
    workflow_id: str,
    *,
    documents: list[DocumentDefSchema],
    rules: list[WorkflowRuleSchema],
    workflow_name: str | None,
    files: list[UploadFile],
    document_types: str | None,
    document_ids: str | None,
) -> RunCreatedResponse | RunPollResponse:
    if not files:
        raise HTTPException(400, "At least one file is required for test run with uploads.")
    bindings = await bindings_from_multipart(
        session,
        workflow_id,
        files,
        document_ids=document_ids,
        document_types=document_types,
    )
    return await start_test_run_session(
        session,
        TestRunSessionRequest(
            workflow_id=workflow_id,
            documents=documents,
            rules=rules,
            workflow_name=workflow_name,
            file_bindings=bindings,
        ),
    )
