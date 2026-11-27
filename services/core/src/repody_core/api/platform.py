"""Health and offline license entitlements endpoints."""

import asyncio

import structlog
from fastapi import APIRouter, Response
from sqlalchemy import text

from repody_common.entitlements import EntitlementState
from repody_core.api.deps import EntitlementDep, require
from repody_core.infra import db
from repody_core.schemas.audit import CoreHealthResponse
from repody_core.settings import get_settings

log = structlog.get_logger(__name__)
router = APIRouter(tags=["platform"])


@router.get("/healthz/live")
async def live() -> CoreHealthResponse:
    """Process liveness probe (no database check)."""
    return CoreHealthResponse(status="ok", oidc_enabled=get_settings().oidc_enabled)


@router.get("/healthz")
async def ready(response: Response) -> CoreHealthResponse:
    """Readiness probe verifying Postgres reachability."""
    settings = get_settings()
    database = False
    try:
        async with asyncio.timeout(settings.health_timeout_seconds):
            async with db.get_session_factory()() as session:
                await session.execute(text("SELECT 1"))
            database = True
    except Exception as exc:
        log.warning("core_health_check_failed", error=repr(exc))
    status = "ok" if database else "degraded"
    if status == "degraded":
        response.status_code = 503
    return CoreHealthResponse(
        status=status,
        database=database,
        oidc_enabled=settings.oidc_enabled,
    )


@router.get("/platform/entitlements", dependencies=[require("case:read")])
async def get_entitlements(provider: EntitlementDep) -> EntitlementState:
    """Return the verified offline Ed25519 license state and active modules."""
    return provider.current()
