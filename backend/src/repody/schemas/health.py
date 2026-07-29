"""OpenAPI schemas for platform health probes."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from repody.schemas.common import CamelModel


class HealthLiveResponse(CamelModel):
    status: Literal["ok"]


class WorkerPoolsHealth(CamelModel):
    fast: str
    extract: str


class HealthReadinessResponse(CamelModel):
    status: Literal["ok", "degraded"]
    redis_ok: bool = Field(serialization_alias="redisOk")
    extractor: str
    inference: str
    llamacpp: bool | None = None
    storage_backend: str = Field(serialization_alias="storageBackend")
    direct_upload_enabled: bool = Field(serialization_alias="directUploadEnabled")
    cache_enabled: bool = Field(serialization_alias="cacheEnabled")
    db_pool_size: int = Field(serialization_alias="dbPoolSize")
    queue_backend: str = Field(serialization_alias="queueBackend")
    structured_llm: bool = Field(serialization_alias="structuredLlm")
    rate_limit_enabled: bool = Field(serialization_alias="rateLimitEnabled")
    queued_runs: int = Field(serialization_alias="queuedRuns")
    running_runs: int = Field(serialization_alias="runningRuns")
    inflight_runs: int = Field(serialization_alias="inflightRuns")
    auth_enabled: bool = Field(serialization_alias="authEnabled")
    oidc_enabled: bool = Field(serialization_alias="oidcEnabled")
    worker_pools: WorkerPoolsHealth = Field(serialization_alias="workerPools")
    taskiq_configured: bool = Field(serialization_alias="taskiqConfigured")
