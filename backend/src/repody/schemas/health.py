"""OpenAPI schemas for platform health probes."""

from __future__ import annotations

from typing import Literal

from repody.schemas.common import CamelModel


class HealthLiveResponse(CamelModel):
    status: Literal["ok"]


class WorkerPoolsHealth(CamelModel):
    fast: str
    extract: str


class HealthReadinessResponse(CamelModel):
    status: Literal["ok", "degraded"]
    redis_ok: bool
    extractor: str
    inference: str
    llamacpp: bool | None = None
    storage_backend: str
    direct_upload_enabled: bool
    cache_enabled: bool
    db_pool_size: int
    queue_backend: str
    structured_llm: bool
    rate_limit_enabled: bool
    queued_runs: int
    running_runs: int
    inflight_runs: int
    auth_enabled: bool
    oidc_enabled: bool
    worker_pools: WorkerPoolsHealth
    taskiq_configured: bool
