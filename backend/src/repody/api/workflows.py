from fastapi import APIRouter, Depends, HTTPException

from repody.api.auth import require_permission
from repody.api.deps import SessionDep
from repody.app.workflow import service as workflow_service
from repody.app.workflow.dry_run import dry_run_workflow
from repody.app.workflow.validation import validate_rules_preview
from repody.schemas.workflow import (
    BulkDeleteWorkflowsBody,
    CreateWorkflowBody,
    DeployWorkflowBody,
    DryRunBody,
    DryRunResponse,
    RuleValidationItem,
    ValidateRulesBody,
    ValidateRulesResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowSchema,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get(
    "",
    response_model=WorkflowListResponse,
    dependencies=[Depends(require_permission("workflow", "read"))],
)
async def list_workflows(session: SessionDep):
    items = await workflow_service.list_workflows(session)
    return WorkflowListResponse(workflows=items)


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=201,
    dependencies=[Depends(require_permission("workflow", "write"))],
)
async def create_workflow(body: CreateWorkflowBody, session: SessionDep):
    wf = await workflow_service.create_workflow(
        session, name=body.name, description=body.description, owner=body.owner
    )
    await session.commit()
    return WorkflowResponse(workflow=wf)


@router.post(
    "/bulk-delete",
    status_code=204,
    dependencies=[Depends(require_permission("workflow", "delete"))],
)
async def bulk_delete_workflows(body: BulkDeleteWorkflowsBody, session: SessionDep):
    await workflow_service.bulk_archive_workflows(session, body.ids)
    await session.commit()


@router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    dependencies=[Depends(require_permission("workflow", "read"))],
)
async def get_workflow(workflow_id: str, session: SessionDep):
    wf = await workflow_service.get_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return WorkflowResponse(workflow=wf)


@router.put(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    dependencies=[Depends(require_permission("workflow", "write"))],
)
async def update_workflow(workflow_id: str, body: WorkflowSchema, session: SessionDep):
    body.id = workflow_id
    try:
        wf = await workflow_service.upsert_workflow(session, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    await session.commit()
    return WorkflowResponse(workflow=wf)


@router.delete(
    "/{workflow_id}",
    status_code=204,
    dependencies=[Depends(require_permission("workflow", "delete"))],
)
async def delete_workflow(workflow_id: str, session: SessionDep):
    ok = await workflow_service.archive_workflow(session, workflow_id)
    if not ok:
        raise HTTPException(404, "Workflow not found")
    await session.commit()


@router.post(
    "/{workflow_id}/deploy",
    response_model=WorkflowResponse,
    dependencies=[Depends(require_permission("workflow", "write"))],
)
async def deploy_workflow(
    workflow_id: str,
    session: SessionDep,
    body: DeployWorkflowBody | None = None,
):
    wf = await workflow_service.deploy_workflow(
        session, workflow_id, api_key=body.api_key if body else None
    )
    if not wf:
        raise HTTPException(404, "Workflow not found")
    await session.commit()
    return WorkflowResponse(workflow=wf)


@router.post(
    "/validate-rules",
    response_model=ValidateRulesResponse,
    dependencies=[Depends(require_permission("workflow", "read"))],
)
async def validate_rules(body: ValidateRulesBody):
    """Authoritative rule validation for the workflow builder."""
    rows = validate_rules_preview(body.rules)
    return ValidateRulesResponse(
        rules=[
            RuleValidationItem(rule_id=row.rule_id, issues=row.issues, checks=row.checks)
            for row in rows
        ]
    )


@router.post(
    "/{workflow_id}/dry-run",
    response_model=DryRunResponse,
    dependencies=[Depends(require_permission("workflow", "write"))],
)
async def dry_run(workflow_id: str, body: DryRunBody):
    """Evaluate the posted draft only; ``workflow_id`` scopes the route, not the data."""
    del workflow_id
    return await dry_run_workflow(body)
