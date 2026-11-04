from __future__ import annotations

from fastapi import APIRouter

from repody.api.deps import SessionDep, require
from repody.app import workflows
from repody.schemas.workflow import (
    BulkDelete,
    CreateWorkflow,
    RuleChecks,
    WorkflowDefinition,
    WorkflowIn,
    WorkflowList,
    WorkflowOut,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", dependencies=[require("workflow:read")])
async def list_workflows(session: SessionDep) -> WorkflowList:
    return WorkflowList(workflows=await workflows.list_workflows(session))


@router.post("", status_code=201, dependencies=[require("workflow:write")])
async def create_workflow(body: CreateWorkflow, session: SessionDep) -> WorkflowOut:
    workflow = await workflows.create_workflow(session, body)
    await session.commit()
    return workflow


@router.post("/bulk-delete", status_code=204, dependencies=[require("workflow:delete")])
async def delete_workflows(body: BulkDelete, session: SessionDep) -> None:
    await workflows.archive_workflows(session, body.ids)
    await session.commit()


@router.post("/check-rules", dependencies=[require("workflow:read")])
async def check_rules(body: WorkflowDefinition) -> RuleChecks:
    """Builder feedback for unsaved rules: what blocks saving, and each condition as text."""
    return RuleChecks(rules=workflows.check_rules(body))


@router.get("/{workflow_id}", dependencies=[require("workflow:read")])
async def get_workflow(workflow_id: str, session: SessionDep) -> WorkflowOut:
    return await workflows.get_workflow(session, workflow_id)


@router.put("/{workflow_id}", dependencies=[require("workflow:write")])
async def save_workflow(workflow_id: str, body: WorkflowIn, session: SessionDep) -> WorkflowOut:
    workflow = await workflows.save_workflow(session, workflow_id, body)
    await session.commit()
    return workflow


@router.delete("/{workflow_id}", status_code=204, dependencies=[require("workflow:delete")])
async def delete_workflow(workflow_id: str, session: SessionDep) -> None:
    await workflows.load(session, workflow_id)
    await workflows.archive_workflows(session, [workflow_id])
    await session.commit()


@router.post("/{workflow_id}/deploy", dependencies=[require("workflow:write")])
async def deploy_workflow(workflow_id: str, session: SessionDep) -> WorkflowOut:
    """Activate the workflow and issue a new API key (shown once)."""
    workflow = await workflows.deploy_workflow(session, workflow_id)
    await session.commit()
    return workflow
