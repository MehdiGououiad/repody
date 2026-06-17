"""Platform liveness and readiness probes."""

from __future__ import annotations

import os

from sqlalchemy import text

from audit_workbench.db import base as db_base
from audit_workbench.schemas.health import (
    HealthLiveResponse,
    HealthReadinessResponse,
    WorkerPoolsHealth,
)
from audit_workbench.services.admission import count_inflight, count_queued, count_running
from audit_workbench.services.document_model_catalog import probe_active_runtime
from audit_workbench.settings import get_settings


async def probe_liveness() -> HealthLiveResponse:
    async with db_base.async_session_factory() as session:
        await session.execute(text("SELECT 1"))
    return HealthLiveResponse(status="ok")


async def probe_readiness() -> HealthReadinessResponse:
    settings = get_settings()
    async with db_base.async_session_factory() as session:
        await session.execute(text("SELECT 1"))
        try:
            queued_runs = await count_queued(session)
            running_runs = await count_running(session)
            inflight_runs = await count_inflight(session)
        except Exception:
            queued_runs = 0
            running_runs = 0
            inflight_runs = 0

    mode = settings.inference_mode.lower()
    inference_reachable = None
    if settings.healthz_probe_inference:
        inference_reachable = await probe_active_runtime(settings)

    return HealthReadinessResponse(
        status="ok",
        extractor=settings.extractor,
        inference=settings.inference_mode,
        model_runner=inference_reachable,
        vllm=inference_reachable if mode == "vllm" else None,
        storage_backend=settings.storage_backend,
        direct_upload_enabled=settings.direct_upload_enabled and settings.storage_backend == "s3",
        cache_enabled=settings.extraction_cache_enabled,
        db_pool_size=settings.db_pool_size,
        queue_backend="hatchet",
        structured_llm=settings.structured_llm_enabled,
        rate_limit_enabled=settings.rate_limit_enabled,
        admission_control_enabled=settings.admission_control_enabled,
        queued_runs=queued_runs,
        running_runs=running_runs,
        inflight_runs=inflight_runs,
        auth_enabled=settings.oidc_enabled,
        oidc_enabled=settings.oidc_enabled,
        worker_pools=WorkerPoolsHealth(
            fast=settings.worker_pool_fast,
            ocr=settings.worker_pool_ocr,
        ),
        hatchet_configured=bool(settings.hatchet_client_token or os.getenv("HATCHET_CLIENT_TOKEN")),
    )
