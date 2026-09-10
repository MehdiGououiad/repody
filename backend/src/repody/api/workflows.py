from fastapi import APIRouter, Depends, HTTPException

from repody.api.deps import SessionDep
from repody.app.workflow import service as workflow_service
from repody.app.workflow.validation import validate_rules_preview
from repody.extraction.pipeline import extract_document_fields
from repody.infra.auth.dependencies import require_permission
from repody.rules.conditions import resolve_rule_body
from repody.rules.runner import evaluate_dry_run_rules
from repody.schemas.workflow import (
    BulkDeleteWorkflowsBody,
    CreateWorkflowBody,
    DeployWorkflowBody,
    DryRunBody,
    DryRunExtracted,
    DryRunResponse,
    DryRunRuleResult,
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
    rows = validate_rules_preview(body.documents, body.rules)
    return ValidateRulesResponse(
        rules=[RuleValidationItem(rule_id=row.rule_id, issues=row.issues) for row in rows]
    )


def _normalize_dry_run_rules(rules: list) -> list[dict]:
    return [
        {
            **r.model_dump(by_alias=False),
            "body": resolve_rule_body(r.model_dump(by_alias=False)),
        }
        for r in rules
    ]


@router.post(
    "/{workflow_id}/dry-run",
    response_model=DryRunResponse,
    dependencies=[Depends(require_permission("workflow", "write"))],
)
async def dry_run(workflow_id: str, body: DryRunBody):
    # workflow_id is declared for routing only: a dry run evaluates the posted
    # draft, never the persisted workflow.
    _ = workflow_id
    fields = body.fields
    rules = _normalize_dry_run_rules(body.rules_full or body.rules)

    schema = [{"name": f.name, "description": f.description} for f in fields if f.name.strip()]
    sample_values = {
        f.name: f.sample_value
        for f in fields
        if f.name.strip() and f.sample_value is not None and f.sample_value.strip()
    }
    dry_fields = extract_document_fields(schema, sample_values=sample_values or None)
    field_values = {row.key: row.value for row in dry_fields if row.key.strip()}
    extracted = [
        DryRunExtracted(field=row.key, value=row.value, matched=row.extracted) for row in dry_fields
    ]

    rule_results = [
        DryRunRuleResult.model_validate(row)
        for row in await evaluate_dry_run_rules(rules, field_values)
    ]
    return DryRunResponse(extracted=extracted, rule_results=rule_results)
