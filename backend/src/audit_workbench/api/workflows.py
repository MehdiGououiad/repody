from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.extraction.stub import extract_document_fields
from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.rules.evaluator import evaluate_dry_run_rules
from audit_workbench.schemas.workflow import (
    BulkDeleteWorkflowsBody,
    CreateWorkflowBody,
    DeployWorkflowBody,
    DryRunBody,
    DryRunExtracted,
    DryRunResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowSchema,
)
from audit_workbench.services import workflow_service

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(session: AsyncSession = Depends(get_session)):
    items = await workflow_service.list_workflows(session)
    return WorkflowListResponse(workflows=items)


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(body: CreateWorkflowBody, session: AsyncSession = Depends(get_session)):
    wf = await workflow_service.create_workflow(
        session, name=body.name, description=body.description, owner=body.owner
    )
    return WorkflowResponse(workflow=wf)


@router.post("/bulk-delete", status_code=204)
async def bulk_delete_workflows(
    body: BulkDeleteWorkflowsBody, session: AsyncSession = Depends(get_session)
):
    await workflow_service.bulk_archive_workflows(session, body.ids)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, session: AsyncSession = Depends(get_session)):
    wf = await workflow_service.get_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return WorkflowResponse(workflow=wf)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str, body: WorkflowSchema, session: AsyncSession = Depends(get_session)
):
    body.id = workflow_id
    try:
        wf = await workflow_service.upsert_workflow(session, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return WorkflowResponse(workflow=wf)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str, session: AsyncSession = Depends(get_session)):
    ok = await workflow_service.archive_workflow(session, workflow_id)
    if not ok:
        raise HTTPException(404, "Workflow not found")


@router.post("/{workflow_id}/deploy", response_model=WorkflowResponse)
async def deploy_workflow(
    workflow_id: str,
    body: DeployWorkflowBody | None = None,
    session: AsyncSession = Depends(get_session),
):
    wf = await workflow_service.deploy_workflow(
        session, workflow_id, api_key=body.api_key if body else None
    )
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return WorkflowResponse(workflow=wf)


@router.post("/{workflow_id}/dry-run", response_model=DryRunResponse)
async def dry_run(workflow_id: str, body: DryRunBody, session: AsyncSession = Depends(get_session)):
    _ = workflow_id
    fields = body.fields
    rules = [
        {
            **r.model_dump(by_alias=False),
            "body": resolve_rule_body(r.model_dump(by_alias=False)),
        }
        for r in body.rules
    ]
    if body.rules_full:
        rules = [
            {
                **r.model_dump(by_alias=False),
                "body": resolve_rule_body(r.model_dump(by_alias=False)),
            }
            for r in body.rules_full
        ]

    schema = [{"name": f.name, "description": f.description} for f in fields if f.name.strip()]
    sample_values = {
        f.name: f.sample_value
        for f in fields
        if f.name.strip() and (f.sample_value or "").strip()
    }
    dry_fields = extract_document_fields(schema, sample_values=sample_values or None)
    field_values = {row.key: row.value for row in dry_fields if row.key.strip()}
    extracted = [
        DryRunExtracted(field=row.key, value=row.value, matched=row.extracted)
        for row in dry_fields
    ]

    rule_results = await evaluate_dry_run_rules(rules, field_values)
    return DryRunResponse(extracted=extracted, rule_results=rule_results)
