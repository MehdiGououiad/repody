"""Central registry of effective model runtime configuration for operators."""

from __future__ import annotations

from typing import Any, Literal

from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID
from audit_workbench.extraction.document_render import RENDER_POLICIES
from audit_workbench.catalog.registry import list_document_models
from audit_workbench.inference.runtime import default_document_runtime
from audit_workbench.schemas.model_runtime import (
    ConfigScope,
    DeploymentNote,
    ModelConfigField,
    ModelRuntimeConfigResponse,
    ModelRuntimeProfile,
    RestartTarget,
)
from audit_workbench.settings import Settings, get_settings


def _display(value: Any) -> str | int | float | bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    return text or None


def _platform_field(
    *,
    key: str,
    env_var: str,
    label: str,
    description: str,
    value: Any,
    restart: RestartTarget = "worker",
    scope: ConfigScope = "platform",
) -> ModelConfigField:
    return ModelConfigField(
        key=key,
        env_var=env_var,
        label=label,
        description=description,
        scope=scope,
        restart=restart,
        value=_display(value),
        configured=value is not None and str(value).strip() != "",
        source="platform",
    )


def _inference_field(
    *,
    key: str,
    env_var: str,
    label: str,
    description: str,
    value: str | int | float | None,
    restart: RestartTarget = "inference",
) -> ModelConfigField:
    return ModelConfigField(
        key=key,
        env_var=env_var,
        label=label,
        description=description,
        scope="inference_server",
        restart=restart,
        value=_display(value),
        configured=False,
        source="host",
    )


def _shared_fields(settings: Settings) -> list[ModelConfigField]:
    return [
        _platform_field(
            key="ocr_max_pages",
            env_var="AUDIT_OCR_MAX_PAGES",
            label="Max PDF pages",
            description="Maximum pages rasterized per document.",
            value=settings.ocr_max_pages,
            restart="worker",
        ),
        _platform_field(
            key="document_render_max_edge_px",
            env_var="AUDIT_DOCUMENT_RENDER_MAX_EDGE_PX",
            label="Bundle render max edge (px)",
            description="Long-edge cap when building the shared document bundle cache.",
            value=settings.document_render_max_edge_px,
            restart="worker",
        ),
        _platform_field(
            key="extraction_cache_enabled",
            env_var="AUDIT_EXTRACTION_CACHE_ENABLED",
            label="Extraction cache",
            description="Redis cache for repeated identical extractions.",
            value=settings.extraction_cache_enabled,
            restart="worker",
        ),
    ]


def _repody_vlm_fields(settings: Settings) -> list[ModelConfigField]:
    runtime = default_document_runtime(settings)
    fields: list[ModelConfigField] = [
        _platform_field(
            key="repody_vlm_enabled",
            env_var="AUDIT_REPODY_VLM_ENABLED",
            label="Enabled",
            description="Register Repody VLM in the catalog.",
            value=settings.repody_vlm_enabled,
            restart="api",
        ),
        _platform_field(
            key="default_ocr_model",
            env_var="AUDIT_DEFAULT_OCR_MODEL",
            label="Default catalog id",
            description="Workflow default when no model is selected.",
            value=settings.default_ocr_model,
            restart="api",
        ),
        _platform_field(
            key="inference_mode",
            env_var="AUDIT_INFERENCE_MODE",
            label="Inference mode",
            description="docker_model_runner or vllm.",
            value=settings.inference_mode,
            restart="worker",
        ),
        _platform_field(
            key="repody_vlm_model",
            env_var="AUDIT_REPODY_VLM_MODEL",
            label="Docker Model Runner id",
            description="Model id when inference_mode=docker_model_runner.",
            value=settings.repody_vlm_model,
            restart="worker",
        ),
        _platform_field(
            key="repody_vlm_max_tokens",
            env_var="AUDIT_REPODY_VLM_MAX_TOKENS",
            label="Max completion tokens",
            description="Token budget for structured field extraction.",
            value=settings.repody_vlm_max_tokens,
            restart="worker",
        ),
        _platform_field(
            key="repody_vlm_max_edge_px",
            env_var="AUDIT_REPODY_VLM_MAX_EDGE_PX",
            label="Page max edge (px)",
            description="Optional downscale before VLM. Empty preserves rendered size.",
            value=settings.repody_vlm_max_edge_px,
            restart="worker",
            scope="worker_runtime",
        ),
        _platform_field(
            key="repody_vlm_pdf_dpi",
            env_var="AUDIT_REPODY_VLM_PDF_DPI",
            label="PDF raster DPI",
            description="DPI when rasterizing PDF pages for VLM.",
            value=settings.repody_vlm_pdf_dpi,
            restart="worker",
            scope="worker_runtime",
        ),
        _platform_field(
            key="repody_vlm_jpeg_quality",
            env_var="AUDIT_REPODY_VLM_JPEG_QUALITY",
            label="JPEG quality",
            description="Fallback JPEG quality for non-PDF inputs.",
            value=settings.repody_vlm_jpeg_quality,
            restart="worker",
            scope="worker_runtime",
        ),
        _platform_field(
            key="repody_vlm_max_pages_per_request",
            env_var="AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST",
            label="Max pages per request",
            description="Pages batched into one VLM call.",
            value=settings.repody_vlm_max_pages_per_request,
            restart="worker",
        ),
        _platform_field(
            key="repody_vlm_markdown_on_extract",
            env_var="AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT",
            label="Markdown extraction",
            description="Allow document-to-markdown when enabled on a workflow document.",
            value=settings.repody_vlm_markdown_on_extract,
            restart="worker",
        ),
        _platform_field(
            key="repody_vlm_markdown_max_tokens",
            env_var="AUDIT_REPODY_VLM_MARKDOWN_MAX_TOKENS",
            label="Markdown max tokens",
            description="Completion budget for markdown conversion.",
            value=settings.repody_vlm_markdown_max_tokens,
            restart="worker",
        ),
        _platform_field(
            key="repody_vlm_enable_thinking",
            env_var="AUDIT_REPODY_VLM_ENABLE_THINKING",
            label="Enable thinking",
            description="NuExtract reasoning mode for difficult layouts.",
            value=settings.repody_vlm_enable_thinking,
            restart="worker",
        ),
        _platform_field(
            key="repody_vlm_timeout_seconds",
            env_var="AUDIT_REPODY_VLM_TIMEOUT_SECONDS",
            label="Request timeout (s)",
            description="HTTP timeout for VLM calls.",
            value=settings.repody_vlm_timeout_seconds,
            restart="worker",
        ),
    ]
    if runtime == "vllm":
        fields.extend(
            [
                _platform_field(
                    key="vllm_base_url",
                    env_var="AUDIT_VLLM_BASE_URL",
                    label="vLLM base URL",
                    description="OpenAI-compatible inference endpoint.",
                    value=settings.vllm_base_url,
                    restart="worker",
                ),
                _platform_field(
                    key="vllm_served_model",
                    env_var="AUDIT_VLLM_SERVED_MODEL",
                    label="vLLM served model",
                    description="Model id exposed by the vLLM server.",
                    value=settings.vllm_served_model,
                    restart="worker",
                ),
            ]
        )
    else:
        fields.append(
            _platform_field(
                key="docker_model_runner_base_url",
                env_var="AUDIT_DOCKER_MODEL_RUNNER_BASE_URL",
                label="Docker Model Runner URL",
                description="Host inference for Repody VLM.",
                value=settings.docker_model_runner_base_url,
                restart="worker",
            )
        )
        fields.extend(
            [
                _inference_field(
                    key="llamacpp_port",
                    env_var="LLAMACPP_PORT",
                    label="llama-server port",
                    description="Host process started by pnpm llamacpp:serve.",
                    value=8000,
                ),
                _inference_field(
                    key="llamacpp_context",
                    env_var="LLAMACPP_CONTEXT",
                    label="llama-server context",
                    description="Context size for NuExtract on host.",
                    value=16384,
                ),
                _inference_field(
                    key="llamacpp_gpu_layers",
                    env_var="LLAMACPP_GPU_LAYERS",
                    label="GPU layers",
                    description="Offloaded layers for llama-server.",
                    value=99,
                ),
            ]
        )
    return fields


def _deployment_notes() -> list[DeploymentNote]:
    return [
        DeploymentNote(
            change_kind="Python / TypeScript code",
            action="Rebuild the affected image, then rollout",
            detail=(
                "Worker extraction logic, API routes, and benchmark scripts are baked into "
                "container images. Use pnpm dev:build to rebuild and redeploy."
            ),
        ),
        DeploymentNote(
            change_kind="AUDIT_* platform env (this panel)",
            action="helm upgrade or edit ConfigMap, then restart pods",
            detail=(
                "Most knobs here map to AUDIT_* variables in the repody-config ConfigMap. "
                "Workers pick them up on restart — no image rebuild."
            ),
        ),
        DeploymentNote(
            change_kind="Host inference (llama-server)",
            action="Edit deploy/llamacpp/*.local.env and restart the host process",
            detail=(
                "NuExtract runs on host llama-server for vLLM mode. "
                "Start with pnpm llamacpp:serve on the host."
            ),
        ),
    ]


def build_model_runtime_config(settings: Settings | None = None) -> ModelRuntimeConfigResponse:
    settings = settings or get_settings()
    profiles: list[ModelRuntimeProfile] = []

    for spec in list_document_models():
        if spec.id == REPODY_VLM_CATALOG_ID:
            fields = _repody_vlm_fields(settings)
            inference_url = (
                settings.vllm_base_url
                if default_document_runtime(settings) == "vllm"
                else settings.docker_model_runner_base_url
            )
        else:
            fields = []
            inference_url = None

        profiles.append(
            ModelRuntimeProfile(
                model_id=spec.id,
                label=spec.label,
                runtime=spec.runtime,
                runtime_model=spec.runtime_model,
                enabled=True,
                inference_url=inference_url,
                render_policy=RENDER_POLICIES.get(spec.id).doc_ref if spec.id in RENDER_POLICIES else "",
                fields=fields,
            )
        )

    if settings.repody_vlm_enabled is False:
        for profile in profiles:
            if profile.model_id == REPODY_VLM_CATALOG_ID:
                profile.enabled = False

    return ModelRuntimeConfigResponse(
        models=profiles,
        shared=_shared_fields(settings),
        deployment_notes=_deployment_notes(),
    )
