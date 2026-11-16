import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated

import structlog
from fastapi import APIRouter, Response
from sqlalchemy import text

from repody.api.deps import OptionalUser, SessionDep, VisitorScope, require
from repody.app.dashboard import get_dashboard
from repody.app.operations import cancel_run, get_operations
from repody.extraction.client import model_available
from repody.infra import db
from repody.infra.auth import User
from repody.schemas.catalog import Catalog, catalog
from repody.schemas.platform import Access, Dashboard, Health, Operations, PlatformConfig
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
    """Postgres answers. The run queue is Hatchet, whose dashboard shows its workers."""
    database = await _answers("database", _database)
    health = Health(
        status="ok" if database else "degraded",
        database=database,
        oidc_enabled=get_settings().oidc_enabled,
    )
    if health.status == "degraded":
        response.status_code = 503
    return health


@router.get("/me")
async def me(user: OptionalUser) -> Access:
    """The caller's roles and permissions (none when signed out)."""
    return user.access() if user else Access(roles=[], permissions=[])


@router.get("/platform/config", dependencies=[require("metrics:read")])
async def platform_config() -> PlatformConfig:
    settings = get_settings()
    return PlatformConfig(
        served_model=settings.llamacpp_served_model,
        # The public playground does not say where the model runs, nor wake it.
        llamacpp_base_url="" if settings.demo_mode else settings.llamacpp_base_url,
        model_available=None if settings.demo_mode else await model_available(),
        max_upload_bytes=settings.max_upload_bytes,
        max_upload_files=settings.max_upload_files,
        max_pages_per_document=settings.max_pages_per_document,
        run_timeout_minutes=settings.run_timeout_minutes,
    )


@router.get("/operations", dependencies=[require("run:read")])
async def operations(session: SessionDep) -> Operations:
    """The control room: runs in flight with their progress, recent failures, throughput."""
    return await get_operations(session)


@router.post("/runs/{run_id}/cancel", status_code=204)
async def cancel(
    run_id: str, session: SessionDep, user: Annotated[User, require("run:execute")]
) -> None:
    """Stop a queued or running run. 409 when it has already finished."""
    await cancel_run(session, run_id, user.subject)


@router.get("/catalog", dependencies=[require("workflow:read")])
async def get_catalog() -> Catalog:
    """Field types the builder offers, and which of them rules compare in order or add up."""
    return catalog()


@router.get("/dashboard", dependencies=[require("metrics:read")])
async def dashboard(session: SessionDep, visitor: VisitorScope) -> Dashboard:
    return await get_dashboard(session, visitor=visitor)
