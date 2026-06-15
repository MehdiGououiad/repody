from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.auth import require_admin
from audit_workbench.api.deps import get_session
from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.workflow import DocumentDefSchema, RunCreatedResponse, WorkflowRuleSchema
from audit_workbench.services.run_service import FileBinding
from audit_workbench.services.test_run_session import (
    TestRunSessionRequest,
    start_test_run_session,
    start_test_run_with_uploads,
)


router = APIRouter(tags=["test-run"])


class TestRunSessionBody(CamelModel):
    documents: list[DocumentDefSchema] = []
    rules: list[WorkflowRuleSchema] = []
    workflow_name: str | None = None
    file_bindings: list[dict] = []


class StoredBinding(CamelModel):
    document_id: str | None = None
    storage_key: str
    mime_type: str
    file_name: str


@router.post(
    "/workflows/{workflow_id}/test-run/session",
    response_model=RunCreatedResponse,
    status_code=202,
)
async def create_test_run_session(
    workflow_id: str,
    body: TestRunSessionBody,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Start a test Run from snapshot + optional pre-uploaded file bindings."""
    bindings: list[FileBinding] | None = None
    if body.file_bindings:
        bindings = [
            FileBinding(
                document_id=b.get("documentId") or b.get("document_id"),
                storage_key=b["storageKey"] if "storageKey" in b else b["storage_key"],
                mime_type=b.get("mimeType") or b.get("mime_type") or "application/octet-stream",
                file_name=b.get("fileName") or b.get("file_name"),
            )
            for b in body.file_bindings
        ]
    result = await start_test_run_session(
        session,
        TestRunSessionRequest(
            workflow_id=workflow_id,
            documents=body.documents,
            rules=body.rules,
            workflow_name=body.workflow_name,
            file_bindings=bindings,
        ),
    )
    if not isinstance(result, RunCreatedResponse):
        raise HTTPException(500, "Unexpected inline test run response")
    return result


@router.post(
    "/workflows/{workflow_id}/test-run/session/upload",
    response_model=RunCreatedResponse,
    status_code=202,
)
async def create_test_run_session_upload(
    workflow_id: str,
    session: AsyncSession = Depends(get_session),
    files: list[UploadFile] = File(...),
    payload: str = Form(...),
    document_types: str | None = Form(None),
    document_ids: str | None = Form(None),
    _: None = Depends(require_admin),
):
    """Start a test Run with multipart files + snapshot in one request."""
    data = json.loads(payload)
    documents = [DocumentDefSchema.model_validate(d) for d in data.get("documents", [])]
    rules = [WorkflowRuleSchema.model_validate(r) for r in data.get("rules", [])]
    workflow_name = data.get("workflowName") or data.get("workflow_name")
    result = await start_test_run_with_uploads(
        session,
        workflow_id,
        documents=documents,
        rules=rules,
        workflow_name=workflow_name,
        files=files,
        document_types=document_types,
        document_ids=document_ids,
    )
    if not isinstance(result, RunCreatedResponse):
        raise HTTPException(500, "Unexpected inline test run response")
    return result
