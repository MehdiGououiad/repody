"""Platform config, model catalog, and document-model diagnostics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from audit_workbench.auth.dependencies import require_permission
from audit_workbench.extraction.document_model_branding import (
    normalize_public_catalog_id,
    public_runtime_model_name,
)
from audit_workbench.extraction.template_type_inference import suggest_template_type
from audit_workbench.schemas.models_catalog import ModelsCatalogResponse
from audit_workbench.schemas.platform import (
    DocumentModelSummary,
    OcrDiagnosticResponse,
    OcrDiagnosticSettingsSchema,
    PlatformConfigResponse,
    SuggestTemplateTypeResponse,
)
from audit_workbench.catalog.api import (
    document_model_summaries,
    fetch_models_catalog,
)
from audit_workbench.catalog.probes import (
    probe_document_model_state,
    reachable_detail,
    run_generation_probe,
    unreachable_detail,
)
from audit_workbench.catalog.runtime_fields import build_model_runtime_config
from audit_workbench.schemas.model_runtime import ModelRuntimeConfigResponse
from audit_workbench.settings import get_settings

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
    models = [DocumentModelSummary(**row) for row in document_model_summaries()]
    return PlatformConfigResponse(
        app_name=settings.app_name,
        extractor=settings.extractor,
        inference_mode=settings.inference_mode,
        storage_backend=settings.storage_backend,
        queue_backend="taskiq",
        direct_upload_enabled=settings.direct_upload_enabled and settings.storage_backend == "s3",
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
        worker_task_timeout_minutes=settings.worker_task_timeout_minutes,
        maintenance_interval_seconds=settings.maintenance_interval_seconds,
        worker_pools={
            "fast": settings.worker_pool_fast,
            "ocr": settings.worker_pool_ocr,
        },
        taskiq_configured=bool(settings.redis_url),
        llm_validation_enabled=settings.llm_validation_enabled,
        gpu_live_probe=settings.gpu_live_probe,
        healthz_probe_inference=settings.healthz_probe_inference,
    )


@router.get(
    "/platform/model-runtime-config",
    response_model=ModelRuntimeConfigResponse,
    dependencies=[Depends(require_permission("settings", "read"))],
)
async def get_model_runtime_config() -> ModelRuntimeConfigResponse:
    """Effective per-model runtime knobs (platform env + host inference reference)."""
    return build_model_runtime_config()


@router.get(
    "/models/catalog",
    response_model=ModelsCatalogResponse,
)
async def get_models_catalog() -> ModelsCatalogResponse:
    """Document and validation model catalog with live availability."""
    return await fetch_models_catalog()


@router.get(
    "/diagnostics/ocr",
    response_model=OcrDiagnosticResponse,
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
async def ocr_diagnostic(
    run_infer: bool = Query(False, description="Run a short Repody VLM probe."),
) -> OcrDiagnosticResponse:
    """Document model runtime status (Docker Model Runner or vLLM)."""
    settings = get_settings()
    state = await probe_document_model_state(settings)
    snapshot = OcrDiagnosticSettingsSchema(
        extractor=settings.extractor,
        inference_mode=settings.inference_mode,
        runtime=state.runtime,
        document_model_pdf_dpi=settings.repody_vlm_pdf_dpi,
        document_model_max_edge_px=settings.repody_vlm_max_edge_px,
        llm_validation_enabled=settings.llm_validation_enabled,
    )
    common = {
        "model": public_runtime_model_name(state.model),
        "runtime": state.runtime,
        "inference_reachable": state.reachable,
        "model_in_registry": state.model_loaded,
        "extractor": settings.extractor,
        "inference_mode": settings.inference_mode,
        "settings": snapshot,
    }
    if not state.reachable or not state.model_loaded:
        detail, hint = unreachable_detail(state.runtime)
        return OcrDiagnosticResponse(ok=False, detail=detail, hint=hint, **common)
    if not run_infer:
        return OcrDiagnosticResponse(
            ok=True,
            detail=reachable_detail(state.runtime, live_probe=settings.gpu_live_probe),
            hint="Add ?run_infer=true to run one billed GPU test.",
            **common,
        )

    probe = await run_generation_probe(settings)
    return OcrDiagnosticResponse(
        ok=probe.ok,
        model_loaded=True,
        infer_ms=probe.infer_ms,
        sample_extracted=True,
        detail=probe.detail,
        hint=probe.hint,
        **common,
    )
