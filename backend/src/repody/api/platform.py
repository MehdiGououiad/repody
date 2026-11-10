import asyncio
from collections.abc import Awaitable, Callable

import structlog
from fastapi import APIRouter, Response
from sqlalchemy import text

from repody.api.deps import SessionDep, require
from repody.app.dashboard import get_dashboard
from repody.extraction.client import model_available
from repody.infra import db
from repody.infra.redis import get_redis
from repody.schemas.catalog import Catalog, catalog
from repody.schemas.platform import Dashboard, Health, PlatformConfig
from repody.settings import get_settings

log = structlog.get_logger(__name__)
router = APIRouter(tags=["platform"])


@router.get("/healthz/live")
async def live() -> Health:
    """The process answers (no dependency checks)."""
    return Health(status="ok", oidc_enabled=get_settings().oidc_enabled)


async def _answers(name: str, probe: Callable[[], Awaitable[object]]) -> bool:
    """Whether a dependency answers within the health timeout (a failure is logged)."""
    try:
        async with asyncio.timeout(get_settings().health_timeout_seconds):
            await probe()
    except Exception as exc:
        log.warning("health_check_failed", dependency=name, error=repr(exc))
        return False
    return True


async def _database() -> None:
    async with db.session_factory() as session:
        await session.execute(text("SELECT 1"))


@router.get("/healthz")
async def ready(response: Response) -> Health:
    """Postgres and Redis answer (checked concurrently)."""
    database, redis = await asyncio.gather(
        _answers("database", _database), _answers("redis", get_redis().ping)
    )
    health = Health(
        status="ok" if database and redis else "degraded",
        database=database,
        redis=redis,
        oidc_enabled=get_settings().oidc_enabled,
    )
    if health.status == "degraded":
        response.status_code = 503
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


@router.get("/catalog", dependencies=[require("workflow:read")])
async def get_catalog() -> Catalog:
    """Field types the builder offers, and which of them rules compare in order or add up."""
    return catalog()


@router.get("/dashboard", dependencies=[require("metrics:read")])
async def dashboard(session: SessionDep) -> Dashboard:
    return await get_dashboard(session)
