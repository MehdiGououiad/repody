from __future__ import annotations

from fastapi import APIRouter, Response

from audit_workbench.schemas.health import HealthLiveResponse, HealthReadinessResponse
from audit_workbench.services.platform_health import (
    is_readiness_ok,
    probe_liveness,
    probe_readiness,
)

router = APIRouter(tags=["health"])


@router.get("/healthz/live", response_model=HealthLiveResponse)
async def health_live() -> HealthLiveResponse:
    """Liveness: process is alive, with no dependency or inference probe."""
    return await probe_liveness()


@router.get("/healthz", response_model=HealthReadinessResponse)
async def health_readiness(response: Response) -> HealthReadinessResponse:
    """Readiness with dependency checks, queue depth, and optional inference probe."""
    body = await probe_readiness()
    if not is_readiness_ok(body):
        response.status_code = 503
    return body
