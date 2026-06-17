from __future__ import annotations

from fastapi import APIRouter

from audit_workbench.schemas.health import HealthLiveResponse, HealthReadinessResponse
from audit_workbench.services.platform_health import probe_liveness, probe_readiness

router = APIRouter(tags=["health"])


@router.get("/healthz/live", response_model=HealthLiveResponse)
async def health_live() -> HealthLiveResponse:
    """Liveness for Docker and load balancers — database ping only, no GPU probe."""
    return await probe_liveness()


@router.get("/healthz", response_model=HealthReadinessResponse)
async def health_readiness() -> HealthReadinessResponse:
    """Readiness with queue depth, storage, and optional inference runtime probe."""
    return await probe_readiness()
