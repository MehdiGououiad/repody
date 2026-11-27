"""Health endpoints for ``repody-fraud``."""

import asyncio

from fastapi import APIRouter, HTTPException

from repody_fraud.api.deps import StoreDep
from repody_fraud.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz/live")
async def live() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get(
    "/healthz",
    responses={503: {"description": "Fraud database unavailable."}},
)
async def ready(store: StoreDep) -> dict[str, object]:
    """Readiness probe checking Postgres/pgvector connectivity."""
    timeout = get_settings().health_timeout_seconds
    try:
        await asyncio.wait_for(store.ping(), timeout=timeout)
    except Exception as exc:
        raise HTTPException(503, "Fraud database unavailable.") from exc
    return {"status": "ok", "database": True}
