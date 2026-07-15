"""Central registry of effective model runtime configuration for operators."""

from __future__ import annotations

from typing import Any, Literal

from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID
from audit_workbench.catalog.registry import list_document_models
from audit_workbench.extraction.document_render import RENDER_POLICIES
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
            key="extraction_cache_enabled",
            env_var="AUDIT_EXTRACTION_CACHE_ENABLED",
            label="Extraction cache",
            description="Redis cache for repeated identical extractions.",
            value=settings.extraction_cache_enabled,
            restart="worker",
        ),
    ]


def _repody_vlm_fields(settings: Settings) -> list[ModelConfigField]:
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
            key="default_document_model_id",
            env_var="AUDIT_DEFAULT_DOCUMENT_MODEL_ID",
            label="Default catalog id",
            description="Workflow default when no model is selected.",
            value=settings.default_document_model_id,
            restart="api",
        ),
        _platform_field(
            key="inference_mode",
            env_var="AUDIT_INFERENCE_MODE",
            label="Inference mode",
            description="llamacpp (local llama-server OpenAI API).",
            value=settings.inference_mode,
            restart="worker",
        ),
        _platform_field(
            key="llamacpp_base_url",
            env_var="AUDIT_LLAMACPP_BASE_URL",
            label="llama-server base URL",
            description="OpenAI-compatible llama-server endpoint.",
            value=settings.llamacpp_base_url,
            restart="worker",
        ),
        _platform_field(
            key="llamacpp_served_model",
            env_var="AUDIT_LLAMACPP_SERVED_MODEL",
            label="Served model id",
            description="Model id exposed by llama-server.",
            value=settings.llamacpp_served_model,
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
            key="repody_vlm_timeout_seconds",
            env_var="AUDIT_REPODY_VLM_TIMEOUT_SECONDS",
            label="Request timeout (s)",
            description="HTTP timeout for VLM calls.",
            value=settings.repody_vlm_timeout_seconds,
            restart="worker",
        ),
        _inference_field(
            key="llamacpp_port",
            env_var="LLAMACPP_PORT",
            label="llama-server port",
            description="Host process started by pnpm llamacpp:serve.",
            value=8081,
        ),
        _inference_field(
            key="llamacpp_context",
            env_var="LLAMACPP_CONTEXT",
            label="llama-server context",
            description="NuExtract official low-memory context (16384).",
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
                "NuExtract runs on host llama-server. "
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
            inference_url = settings.llamacpp_base_url
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
