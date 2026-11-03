"""Platform config, model catalog, and schema type suggestion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from repody.api.auth import require_permission
from repody.app.uploads.service import presign_supported
from repody.catalog.api import document_model_summaries, fetch_models_catalog
from repody.extraction.branding import REPODY_VLM_CATALOG_ID
from repody.extraction.nuextract import suggest_template_type
from repody.schemas.models_catalog import ModelsCatalogResponse
from repody.schemas.platform import (
    DocumentModelSummary,
    PlatformConfigResponse,
    SuggestTemplateTypeResponse,
)
from repody.settings import get_settings

router = APIRouter(tags=["platform"])


@router.get(
    "/schema/suggest-type",
    response_model=SuggestTemplateTypeResponse,
    dependencies=[Depends(require_permission("workflow", "read"))],
)
async def suggest_schema_template_type(
    name: str = Query("", description="Field name"),
    description: str = Query("", description="What to extract"),
) -> SuggestTemplateTypeResponse:
    """Infer a NuExtract template leaf type from field name and intent."""
    return SuggestTemplateTypeResponse(template_type=suggest_template_type(name, description))


@router.get(
    "/platform/config",
    response_model=PlatformConfigResponse,
    dependencies=[Depends(require_permission("settings", "read"))],
)
async def get_platform_config() -> PlatformConfigResponse:
    """Read-only platform configuration snapshot (safe AUDIT_* fields)."""
    settings = get_settings()
    return PlatformConfigResponse(
        app_name=settings.app_name,
        extractor=settings.extractor,
        inference_mode=settings.inference_mode,
        storage_backend=settings.storage_backend,
        queue_backend="taskiq",
        direct_upload_enabled=presign_supported(settings),
        cache_enabled=settings.extraction_cache_enabled,
        rate_limit_enabled=settings.rate_limit_enabled,
        default_document_model_id=REPODY_VLM_CATALOG_ID,
        default_read_path="document_model",
        document_models=[DocumentModelSummary(**row) for row in document_model_summaries()],
        nuextract_max_pages_per_request=settings.repody_vlm_max_pages_per_request,
        llamacpp_base_url=settings.llamacpp_base_url,
        max_upload_bytes=settings.max_upload_bytes,
        max_upload_files=settings.max_upload_files,
        stale_run_timeout_minutes=settings.stale_run_timeout_minutes,
        queued_stale_timeout_minutes=settings.queued_stale_timeout_minutes,
        worker_task_timeout_minutes=settings.worker_task_timeout_minutes,
        maintenance_interval_seconds=settings.maintenance_interval_seconds,
        worker_pools={"fast": settings.worker_pool_fast, "extract": settings.worker_pool_extract},
        taskiq_configured=bool(settings.redis_url),
        healthz_probe_inference=settings.healthz_probe_inference,
    )


@router.get(
    "/models/catalog",
    response_model=ModelsCatalogResponse,
    dependencies=[Depends(require_permission("models", "read"))],
)
async def get_models_catalog() -> ModelsCatalogResponse:
    """The document model with live availability from the llama-server."""
    return await fetch_models_catalog()
