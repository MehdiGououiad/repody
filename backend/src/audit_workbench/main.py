from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from audit_workbench.api import (
    audits,
    diagnostics,
    inference,
    models_catalog,
    ocr,
    platform,
    processing_paths,
    metrics,
    operator,
    rules_library,
    runs,
    test_run,
    uploads,
    workflows,
)
from audit_workbench.api.auth import require_admin
from audit_workbench.db.base import Base, async_session_factory, engine
from audit_workbench.db.seed import seed_database
from audit_workbench.inference.http_pool import close_async_http_client
from audit_workbench.observability.bootstrap import init_observability
from audit_workbench.observability.middleware import RequestLoggingMiddleware
from audit_workbench.observability.tracing import instrument_fastapi
from audit_workbench.services.run_dispatch import close_hatchet_client
from audit_workbench.services.rate_limit import GlobalRateLimitMiddleware
from audit_workbench.services.redis_pool import close_redis_pool
from audit_workbench.settings import get_settings
from audit_workbench.storage.factory import init_storage

log = structlog.get_logger(__name__)
_admin = [Depends(require_admin)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = init_observability()
    log.info(
        "application_starting",
        event_domain="platform",
        auth_enabled=settings.auth_enabled,
        storage_backend=settings.storage_backend,
        inference_mode=settings.inference_mode,
        run_jobs_inline=settings.run_jobs_inline,
    )
    if settings.use_create_all:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("database_schema_create_all", event_domain="platform")
    await init_storage()
    maintenance_stop = asyncio.Event()
    maintenance_task: asyncio.Task | None = None
    if not settings.run_jobs_inline:
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
    if maintenance_task is not None:
        await maintenance_task
    await close_hatchet_client()
    await close_redis_pool()
    await close_async_http_client()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
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

    @app.get("/v1/healthz/live")
    async def healthz_live():
        """Liveness for Docker/load balancers — DB only, no GPU probe."""
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/v1/healthz")
    async def healthz():
        from audit_workbench.services.document_model_catalog import probe_active_runtime

        from audit_workbench.services.admission import count_inflight, count_queued

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            try:
                queued_runs = await count_queued(session)
                inflight_runs = await count_inflight(session)
            except Exception:
                queued_runs = 0
                inflight_runs = 0
        mode = settings.inference_mode.lower()
        inference_reachable = None
        if settings.healthz_probe_inference:
            inference_reachable = await probe_active_runtime(settings)
        return {
            "status": "ok",
            "extractor": settings.extractor,
            "inference": settings.inference_mode,
            "modelRunner": inference_reachable,
            "vllm": inference_reachable if mode == "vllm" else None,
            "storageBackend": settings.storage_backend,
            "directUploadEnabled": settings.direct_upload_enabled
            and settings.storage_backend == "s3",
            "cacheEnabled": settings.extraction_cache_enabled,
            "dbPoolSize": settings.db_pool_size,
            "queueBackend": "hatchet",
            "structuredLlm": settings.structured_llm_enabled,
            "rateLimitEnabled": settings.rate_limit_enabled,
            "admissionControlEnabled": settings.admission_control_enabled,
            "queuedRuns": queued_runs,
            "inflightRuns": inflight_runs,
            "authEnabled": settings.auth_enabled,
            "workerPools": {
                "fast": settings.worker_pool_fast,
                "ocr": settings.worker_pool_ocr,
            },
            "hatchetConfigured": bool(
                settings.hatchet_client_token
                or os.getenv("HATCHET_CLIENT_TOKEN")
                or settings.run_jobs_inline
            ),
        }

    app.include_router(workflows.router, prefix="/v1", dependencies=_admin)
    app.include_router(runs.router, prefix="/v1")
    app.include_router(audits.router, prefix="/v1", dependencies=_admin)
    app.include_router(metrics.router, prefix="/v1", dependencies=_admin)
    app.include_router(rules_library.router, prefix="/v1", dependencies=_admin)
    app.include_router(uploads.router, prefix="/v1", dependencies=_admin)
    app.include_router(diagnostics.router, prefix="/v1", dependencies=_admin)
    app.include_router(platform.router, prefix="/v1", dependencies=_admin)
    app.include_router(inference.router, prefix="/v1", dependencies=_admin)
    app.include_router(ocr.router, prefix="/v1", dependencies=_admin)
    app.include_router(models_catalog.router, prefix="/v1", dependencies=_admin)
    app.include_router(test_run.router, prefix="/v1", dependencies=_admin)
    app.include_router(processing_paths.router, prefix="/v1", dependencies=_admin)
    app.include_router(operator.router, prefix="/v1", dependencies=_admin)

    instrument_fastapi(app, settings)

    return app


app = create_app()
