"""OpenAPI schemas for platform health probes."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from audit_workbench.schemas.common import CamelModel


class HealthLiveResponse(CamelModel):
    status: Literal["ok"]


class WorkerPoolsHealth(CamelModel):
    fast: str
    ocr: str


class HealthReadinessResponse(CamelModel):
    status: Literal["ok"]
    extractor: str
    inference: str
    model_runner: bool | None = Field(serialization_alias="modelRunner")
    vllm: bool | None = None
    storage_backend: str = Field(serialization_alias="storageBackend")
    direct_upload_enabled: bool = Field(serialization_alias="directUploadEnabled")
    cache_enabled: bool = Field(serialization_alias="cacheEnabled")
    db_pool_size: int = Field(serialization_alias="dbPoolSize")
    queue_backend: str = Field(serialization_alias="queueBackend")
    structured_llm: bool = Field(serialization_alias="structuredLlm")
    rate_limit_enabled: bool = Field(serialization_alias="rateLimitEnabled")
    admission_control_enabled: bool = Field(serialization_alias="admissionControlEnabled")
    queued_runs: int = Field(serialization_alias="queuedRuns")
    running_runs: int = Field(serialization_alias="runningRuns")
    inflight_runs: int = Field(serialization_alias="inflightRuns")
    auth_enabled: bool = Field(serialization_alias="authEnabled")
    oidc_enabled: bool = Field(serialization_alias="oidcEnabled")
    worker_pools: WorkerPoolsHealth = Field(serialization_alias="workerPools")
    taskiq_configured: bool = Field(serialization_alias="taskiqConfigured")
