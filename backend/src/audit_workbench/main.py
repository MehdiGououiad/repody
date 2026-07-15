from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from audit_workbench.api import (
    audits,
    dashboard,
    health,
    iam,
    metrics,
    operator,
    platform,
    rules_library,
    runs,
    uploads,
    workflows,
)
from audit_workbench.api.openapi_config import install_openapi
from audit_workbench.auth.dependencies import require_permission
from audit_workbench.db.base import async_session_factory, engine
from audit_workbench.db.seed import seed_database
from audit_workbench.inference.openai_compat import close_openai_clients
from audit_workbench.observability.bootstrap import init_observability
from audit_workbench.observability.middleware import RequestLoggingMiddleware
from audit_workbench.observability.tracing import instrument_fastapi
from audit_workbench.services.rate_limit import GlobalRateLimitMiddleware
from audit_workbench.services.redis_pool import close_redis_pool
from audit_workbench.services.run_dispatch import close_taskiq_brokers
from audit_workbench.settings import get_settings
from audit_workbench.storage.factory import init_storage

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = init_observability()
    log.info(
        "application_starting",
        event_domain="platform",
        oidc_enabled=settings.oidc_enabled,
        storage_backend=settings.storage_backend,
        inference_mode=settings.inference_mode,
    )
    from audit_workbench.services.operator import hydrate_operator_jobs_from_redis
    from audit_workbench.taskiq.broker import startup_taskiq_brokers

    # Independent startup work — FastAPI lifespan guidance: keep critical path short.
    await asyncio.gather(
        init_storage(),
        hydrate_operator_jobs_from_redis(),
        startup_taskiq_brokers(),
    )
    if settings.oidc_enabled:
        from audit_workbench.auth.jwt_validator import warm_jwks_cache

        try:
            await warm_jwks_cache(settings)
        except Exception as exc:
            log.warning(
                "oidc_jwks_warmup_failed",
                event_domain="platform",
                error=str(exc),
            )
    maintenance_stop = asyncio.Event()
    from audit_workbench.services.maintenance import maintenance_loop, run_maintenance_cycle

    await run_maintenance_cycle()
    maintenance_task = asyncio.create_task(maintenance_loop(maintenance_stop))
    if settings.seed_on_startup:
        async with async_session_factory() as session:
            await seed_database(session)
            await session.commit()
            log.info("database_seeded", event_domain="platform")
    yield
    log.info("application_shutting_down", event_domain="platform")
    maintenance_stop.set()
    await maintenance_task
    from audit_workbench.services.dispatch_outbox import drain_dispatch_tasks

    await drain_dispatch_tasks()
    await close_taskiq_brokers()
    await close_redis_pool()
    await close_openai_clients()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(GlobalRateLimitMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/v1")
    app.include_router(workflows.router, prefix="/v1")
    app.include_router(runs.router, prefix="/v1")
    app.include_router(
        audits.router,
        prefix="/v1",
        dependencies=[Depends(require_permission("audit", "read"))],
    )
    app.include_router(
        metrics.router,
        prefix="/v1",
        dependencies=[Depends(require_permission("metrics", "read"))],
    )
    app.include_router(
        dashboard.router,
        prefix="/v1",
        dependencies=[Depends(require_permission("metrics", "read"))],
    )
    app.include_router(
        rules_library.router,
        prefix="/v1",
        dependencies=[Depends(require_permission("rules", "read"))],
    )
    app.include_router(
        uploads.router,
        prefix="/v1",
        dependencies=[Depends(require_permission("upload", "write"))],
    )
    app.include_router(platform.router, prefix="/v1")
    app.include_router(operator.router, prefix="/v1")
    app.include_router(iam.router, prefix="/v1")

    install_openapi(app)
    instrument_fastapi(app, settings)

    return app


app = create_app()
