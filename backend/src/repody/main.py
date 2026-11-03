from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from repody.api import (
    audits,
    config,
    dashboard,
    health,
    metrics,
    rules_library,
    runs,
    uploads,
    workflows,
)
from repody.api.errors import app_error_handler
from repody.api.openapi_config import install_openapi
from repody.app.ops.maintenance import maintenance_loop, run_maintenance_cycle
from repody.app.run.dispatch import close_taskiq_brokers
from repody.inference.openai_compat import close_openai_clients
from repody.infra.auth.jwt_validator import warm_jwks_cache
from repody.infra.db.base import async_session_factory, engine
from repody.infra.db.seed import seed_database
from repody.infra.http import close_http_clients
from repody.infra.observability.bootstrap import init_observability
from repody.infra.observability.middleware import RequestLoggingMiddleware
from repody.infra.observability.tracing import instrument_fastapi
from repody.infra.rate_limit import GlobalRateLimitMiddleware
from repody.infra.redis.pool import close_redis_pool
from repody.infra.storage.factory import init_storage
from repody.runtime.contracts.result import AppError
from repody.settings import get_settings
from repody.taskiq.broker import startup_taskiq_brokers

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    log.info(
        "application_starting",
        event_domain="platform",
        oidc_enabled=settings.oidc_enabled,
        llamacpp_base_url=settings.llamacpp_base_url,
    )
    await asyncio.gather(init_storage(), startup_taskiq_brokers())
    if settings.oidc_enabled:
        try:
            await warm_jwks_cache(settings)
        except Exception as exc:
            log.warning(
                "oidc_jwks_warmup_failed",
                event_domain="platform",
                error=str(exc),
            )
    maintenance_stop = asyncio.Event()
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
    await close_taskiq_brokers()
    await close_redis_pool()
    await close_openai_clients()
    await close_http_clients()
    await engine.dispose()


def create_app() -> FastAPI:
    # Sentry/Bugsink: init as early as possible (before FastAPI construction).
    settings = init_observability()
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

    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health.router, prefix="/v1")
    app.include_router(workflows.router, prefix="/v1")
    app.include_router(runs.router, prefix="/v1")
    app.include_router(audits.router, prefix="/v1")
    app.include_router(metrics.router, prefix="/v1")
    app.include_router(dashboard.router, prefix="/v1")
    app.include_router(rules_library.router, prefix="/v1")
    app.include_router(uploads.router, prefix="/v1")
    app.include_router(config.router, prefix="/v1")

    install_openapi(app)
    instrument_fastapi(app, settings)

    return app


app = create_app()
