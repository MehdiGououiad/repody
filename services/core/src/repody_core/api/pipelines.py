"""Durable multi-module pipeline routes."""

from typing import Annotated

from fastapi import APIRouter

from repody_core.api.deps import DispatcherDep, EntitlementDep, StoreDep, require
from repody_core.app import pipelines as app_pipelines
from repody_core.infra.auth import CoreUser
from repody_core.schemas.pipelines import PipelineRunResponse, StartPipelineRequest

router = APIRouter(tags=["pipelines"])


@router.post("/cases/{case_id}/pipelines", status_code=202)
async def start_pipeline(
    case_id: str,
    body: StartPipelineRequest,
    store: StoreDep,
    dispatcher: DispatcherDep,
    entitlements: EntitlementDep,
    user: Annotated[CoreUser, require("case:write")],
) -> PipelineRunResponse:
    """Start a durable cross-module pipeline for an existing case."""
    return await app_pipelines.start_pipeline(
        store,
        dispatcher,
        entitlements,
        case_id=case_id,
        actor_sub=user.subject,
        account_id=user.account,
        request=body,
    )


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    store: StoreDep,
    user: Annotated[CoreUser, require("case:read")],
) -> PipelineRunResponse:
    """Retrieve a pipeline run scoped to the caller's account."""
    return await app_pipelines.get_pipeline(
        store,
        pipeline_id=pipeline_id,
        account_id=user.account,
    )
