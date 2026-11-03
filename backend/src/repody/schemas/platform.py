"""Platform config and diagnostics API schemas."""

from __future__ import annotations

from pydantic import Field

from repody.schemas.common import CamelModel


class DocumentModelSummary(CamelModel):
    id: str
    label: str
    runtime: str
    runtime_model: str


class PlatformConfigResponse(CamelModel):
    app_name: str
    extractor: str
    inference_mode: str
    storage_backend: str
    queue_backend: str
    direct_upload_enabled: bool
    cache_enabled: bool
    rate_limit_enabled: bool
    default_document_model_id: str
    default_read_path: str
    document_models: list[DocumentModelSummary]
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


class SuggestTemplateTypeResponse(CamelModel):
    template_type: str
