from __future__ import annotations

from fastapi import APIRouter, Response
from sqlalchemy import text

from repody import db
from repody.api.deps import SessionDep, require
from repody.app.dashboard import get_dashboard
from repody.extraction.client import model_available
from repody.redis_pool import get_redis
from repody.schemas.platform import Dashboard, Health, PlatformConfig
from repody.settings import get_settings

router = APIRouter(tags=["platform"])


@router.get("/healthz/live")
async def live() -> Health:
    """The process answers (no dependency checks)."""
    return Health(status="ok", oidc_enabled=get_settings().oidc_enabled)


@router.get("/healthz")
async def ready(response: Response) -> Health:
    """Postgres and Redis answer."""

    async def check(probe) -> bool:
        try:
            await probe()
            return True
        except Exception:
            return False

    async def database() -> None:
        async with db.session_factory() as session:
            await session.execute(text("SELECT 1"))

    health = Health(
        status="ok",
        database=await check(database),
        redis=await check(get_redis().ping),
        oidc_enabled=get_settings().oidc_enabled,
    )
    if not (health.database and health.redis):
        health.status, response.status_code = "degraded", 503
    return health


@router.get("/platform/config", dependencies=[require("metrics:read")])
async def platform_config() -> PlatformConfig:
    settings = get_settings()
    return PlatformConfig(
        served_model=settings.llamacpp_served_model,
        llamacpp_base_url=settings.llamacpp_base_url,
        model_available=await model_available(),
        cache_enabled=settings.extraction_cache_ttl_seconds > 0,
        max_upload_bytes=settings.max_upload_bytes,
        max_upload_files=settings.max_upload_files,
        max_pages_per_document=settings.max_pages_per_document,
        run_timeout_minutes=settings.run_timeout_minutes,
    )


@router.get("/dashboard", dependencies=[require("metrics:read")])
async def dashboard(session: SessionDep) -> Dashboard:
    return await get_dashboard(session)
