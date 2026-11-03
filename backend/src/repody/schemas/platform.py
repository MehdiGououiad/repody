"""Platform config and diagnostics API schemas."""

from __future__ import annotations

from pydantic import Field

from repody.schemas.common import CamelModel


class PlatformConfigResponse(CamelModel):
    app_name: str
    queue_backend: str
    direct_upload_enabled: bool
    cache_enabled: bool
    rate_limit_enabled: bool
    served_model: str
    nuextract_max_pages_per_request: int | None = None
    llamacpp_base_url: str
    max_upload_bytes: int
    max_upload_files: int
    stale_run_timeout_minutes: int
    queued_stale_timeout_minutes: int
    worker_task_timeout_minutes: int
    maintenance_interval_seconds: int
    worker_pools: dict[str, str] = Field(default_factory=dict)
    taskiq_configured: bool = False
    healthz_probe_inference: bool = False
