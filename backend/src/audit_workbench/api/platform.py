"""Read-only platform configuration snapshot (safe AUDIT_* fields)."""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import Field

from audit_workbench.extraction.document_model_branding import (
    normalize_public_catalog_id,
    public_runtime_model_name,
    public_runtime_name,
)
from audit_workbench.extraction.model_registry import list_document_models
from audit_workbench.schemas.common import CamelModel
from audit_workbench.settings import get_settings

router = APIRouter(tags=["platform"])


class DocumentModelSummary(CamelModel):
    id: str
    label: str
    runtime: str
    runtime_model: str = Field(serialization_alias="runtimeModel")


class PlatformConfigResponse(CamelModel):
    app_name: str
    extractor: str
    inference_mode: str
    storage_backend: str
    queue_backend: str
    run_jobs_inline: bool
    direct_upload_enabled: bool
    cache_enabled: bool
    rate_limit_enabled: bool
    structured_llm: bool
    default_ocr_model: str = Field(serialization_alias="defaultOcrModel")
    default_read_path: str = Field(serialization_alias="defaultReadPath")
    document_models: list[DocumentModelSummary] = Field(serialization_alias="documentModels")
    ocr_max_pages: int = Field(serialization_alias="ocrMaxPages")
    docker_model_runner_base_url: str = Field(serialization_alias="dockerModelRunnerBaseUrl")
    vllm_base_url: str = Field(serialization_alias="vllmBaseUrl")
    max_upload_bytes: int = Field(serialization_alias="maxUploadBytes")
    max_upload_files: int = Field(serialization_alias="maxUploadFiles")
    stale_run_timeout_minutes: int = Field(serialization_alias="staleRunTimeoutMinutes")
    queued_stale_timeout_minutes: int = Field(serialization_alias="queuedStaleTimeoutMinutes")
    hatchet_task_timeout_minutes: int = Field(serialization_alias="hatchetTaskTimeoutMinutes")
    maintenance_interval_seconds: int = Field(serialization_alias="maintenanceIntervalSeconds")
    worker_pools: dict[str, str] = Field(default_factory=dict, serialization_alias="workerPools")
    hatchet_configured: bool = Field(default=False, serialization_alias="hatchetConfigured")
    llm_validation_enabled: bool = Field(default=False, serialization_alias="llmValidationEnabled")
    gpu_live_probe: bool = Field(default=False, serialization_alias="gpuLiveProbe")
    healthz_probe_inference: bool = Field(
        default=False, serialization_alias="healthzProbeInference"
    )


@router.get("/platform/config", response_model=PlatformConfigResponse)
async def get_platform_config() -> PlatformConfigResponse:
    settings = get_settings()
    models = [
        DocumentModelSummary(
            id=spec.id,
            label=spec.label,
            runtime=public_runtime_name(spec.runtime),
            runtime_model=public_runtime_model_name(spec.runtime_model),
        )
        for spec in list_document_models()
    ]
    return PlatformConfigResponse(
        app_name=settings.app_name,
        extractor=settings.extractor,
        inference_mode=settings.inference_mode,
        storage_backend=settings.storage_backend,
        queue_backend="inline" if settings.run_jobs_inline else "hatchet",
        run_jobs_inline=settings.run_jobs_inline,
        direct_upload_enabled=settings.direct_upload_enabled
        and settings.storage_backend == "s3",
        cache_enabled=settings.extraction_cache_enabled,
        rate_limit_enabled=settings.rate_limit_enabled,
        structured_llm=settings.structured_llm_enabled,
        default_ocr_model=normalize_public_catalog_id(settings.default_ocr_model),
        default_read_path="document_model",
        document_models=models,
        ocr_max_pages=settings.ocr_max_pages,
        docker_model_runner_base_url=settings.docker_model_runner_base_url,
        vllm_base_url=settings.vllm_base_url,
        max_upload_bytes=settings.max_upload_bytes,
        max_upload_files=settings.max_upload_files,
        stale_run_timeout_minutes=settings.stale_run_timeout_minutes,
        queued_stale_timeout_minutes=settings.queued_stale_timeout_minutes,
        hatchet_task_timeout_minutes=settings.hatchet_task_timeout_minutes,
        maintenance_interval_seconds=settings.maintenance_interval_seconds,
        worker_pools={
            "fast": settings.worker_pool_fast,
            "ocr": settings.worker_pool_ocr,
        },
        hatchet_configured=bool(
            settings.hatchet_client_token
            or os.getenv("HATCHET_CLIENT_TOKEN")
            or settings.run_jobs_inline
        ),
        llm_validation_enabled=settings.llm_validation_enabled,
        gpu_live_probe=settings.gpu_live_probe,
        healthz_probe_inference=settings.healthz_probe_inference,
    )
