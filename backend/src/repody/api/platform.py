"""Health, the caller's access, platform settings, the dashboard and the control room."""

import asyncio
import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import APIRouter, Response
from sqlalchemy import text

from repody.api.deps import AccountScope, OptionalUser, SessionDep, require
from repody.app.credits import credits_of, run_cost
from repody.app.dashboard import get_dashboard
from repody.app.operations import get_operations
from repody.extraction import client as inference
from repody.infra import db
from repody.schemas.catalog import Catalog, catalog
from repody.schemas.platform import Access, Dashboard, Health, Operations, PlatformConfig
from repody.settings import get_settings

log = structlog.get_logger(__name__)
router = APIRouter(tags=["platform"])

WAKE_COOLDOWN_SECONDS = 60.0
_last_wake: float | None = None
_wake_tasks: set[asyncio.Task[None]] = set()


async def _noop() -> None:
    pass


async def _wake_in_background() -> None:
    try:
        await inference.wake(_noop)
    except Exception as exc:
        log.warning("model_wake_failed", error=repr(exc))


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
async def me(user: OptionalUser, session: SessionDep) -> Access:
    """The caller's roles, permissions and credits (none when signed out)."""
    if user is None:
        return Access(roles=[], permissions=[])
    access = user.access()
    access.credits = await credits_of(session, user.account)
    return access


@router.get("/platform/config", dependencies=[require("metrics:read")])
async def platform_config() -> PlatformConfig:
    settings = get_settings()
    return PlatformConfig(
        served_model=settings.inference_model,
        inference_base_url=settings.inference_base_url,
        model_available=await inference.model_available(),
        max_upload_bytes=settings.max_upload_bytes,
        max_upload_files=settings.max_upload_files,
        max_pages_per_document=settings.max_pages_per_document,
        run_timeout_minutes=settings.run_timeout_minutes,
    )


@router.get("/operations", dependencies=[require("run:read")])
async def operations(session: SessionDep, account: AccountScope) -> Operations:
    """The control room: runs in flight with their progress, recent failures, throughput."""
    return await get_operations(session, account=account)


@router.get("/catalog", dependencies=[require("workflow:read")])
async def get_catalog() -> Catalog:
    """Field types the builder offers, and which of them rules compare in order or add up."""
    return catalog()


@router.post("/model/wake", status_code=202, dependencies=[require("run:execute")])
async def wake_model(user: OptionalUser, session: SessionDep) -> None:
    """Start waking the model server in the background, at most once per minute per process.
    An account that cannot pay for a run wakes nothing: the GPU is billed while it is up."""
    global _last_wake
    if user is not None:
        credits = await credits_of(session, user.account)
        if credits.enforced and credits.balance < run_cost(1):
            return
    now = time.monotonic()
    if _last_wake is not None and now - _last_wake < WAKE_COOLDOWN_SECONDS:
        return
    _last_wake = now
    # Keep a reference until it finishes (asyncio docs, create_task: the loop keeps weak ones).
    task = asyncio.create_task(_wake_in_background())
    _wake_tasks.add(task)
    task.add_done_callback(_wake_tasks.discard)


@router.get("/dashboard", dependencies=[require("metrics:read")])
async def dashboard(session: SessionDep, account: AccountScope) -> Dashboard:
    return await get_dashboard(session, account=account)
