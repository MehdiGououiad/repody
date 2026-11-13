from typing import Annotated

from fastapi import APIRouter, Path

from repody.api.deps import SessionDep, VisitorScope, require
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

# Ids are created by the server (`wf-<uuid7>`) or by the builder for a new draft.
WorkflowId = Annotated[str, Path(max_length=64)]


@router.get("", dependencies=[require("workflow:read")])
async def list_workflows(session: SessionDep, visitor: VisitorScope) -> WorkflowList:
    return WorkflowList(workflows=await workflows.list_workflows(session, visitor=visitor))


@router.post("", status_code=201, dependencies=[require("workflow:write")])
async def create_workflow(
    body: CreateWorkflow, session: SessionDep, visitor: VisitorScope
) -> WorkflowOut:
    workflow = await workflows.create_workflow(session, body, visitor=visitor)
    await session.commit()
    return workflow


@router.post("/bulk-delete", status_code=204, dependencies=[require("workflow:delete")])
async def delete_workflows(body: BulkDelete, session: SessionDep, visitor: VisitorScope) -> None:
    await workflows.archive_workflows(session, body.ids, visitor=visitor)
    await session.commit()


@router.post("/check-rules", dependencies=[require("workflow:read")])
async def check_rules(body: WorkflowDefinition) -> RuleChecks:
    """Builder feedback for unsaved rules: what blocks saving, and each condition as text."""
    return RuleChecks(rules=workflows.check_rules(body))


@router.get("/{workflow_id}", dependencies=[require("workflow:read")])
async def get_workflow(
    workflow_id: WorkflowId, session: SessionDep, visitor: VisitorScope
) -> WorkflowOut:
    return await workflows.get_workflow(session, workflow_id, visitor=visitor)


@router.put("/{workflow_id}", dependencies=[require("workflow:write")])
async def save_workflow(
    workflow_id: WorkflowId, body: WorkflowIn, session: SessionDep, visitor: VisitorScope
) -> WorkflowOut:
    workflow = await workflows.save_workflow(session, workflow_id, body, visitor=visitor)
    await session.commit()
    return workflow


@router.delete("/{workflow_id}", status_code=204, dependencies=[require("workflow:delete")])
async def delete_workflow(
    workflow_id: WorkflowId, session: SessionDep, visitor: VisitorScope
) -> None:
    await workflows.archive_workflow(session, workflow_id, visitor=visitor)
    await session.commit()


@router.post("/{workflow_id}/duplicate", status_code=201, dependencies=[require("workflow:write")])
async def duplicate_workflow(
    workflow_id: WorkflowId, body: CreateWorkflow, session: SessionDep, visitor: VisitorScope
) -> WorkflowOut:
    """A new draft with the same documents and rules, named ``body.name``."""
    workflow = await workflows.duplicate_workflow(session, workflow_id, body, visitor=visitor)
    await session.commit()
    return workflow


@router.post("/{workflow_id}/deploy", dependencies=[require("workflow:deploy")])
async def deploy_workflow(workflow_id: WorkflowId, session: SessionDep) -> WorkflowOut:
    """Activate the workflow and issue a new API key (shown once)."""
    workflow = await workflows.deploy_workflow(session, workflow_id)
    await session.commit()
    return workflow
