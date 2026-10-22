"""Central registry of effective model runtime configuration for operators."""

from __future__ import annotations

from typing import Any

from repody.catalog.registry import list_document_models
from repody.extraction.branding import (
    GLM_OCR_QWEN_CATALOG_ID,
    PADDLEOCR_QWEN_CATALOG_ID,
    REPODY_VLM_CATALOG_ID,
    REPODY_VLM_CLOUD_CATALOG_ID,
)
from repody.extraction.render import RENDER_POLICIES
from repody.schemas.model_runtime import (
    ConfigScope,
    DeploymentNote,
    ModelConfigField,
    ModelRuntimeConfigResponse,
    ModelRuntimeProfile,
    RestartTarget,
)
from repody.settings import Settings, get_settings


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
            description=(
                "When true, run markdown alongside structured NuExtract extraction "
                "(second model call). Markdown-only documents always use markdown when "
                "enabled on the workflow document."
            ),
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


def _nuextract_cloud_fields(settings: Settings) -> list[ModelConfigField]:
    return [
        _platform_field(
            key="nuextract_cloud_enabled",
            env_var="AUDIT_NUEXTRACT_CLOUD_ENABLED",
            label="Enabled",
            description="Register NuExtract Cloud in the catalog.",
            value=settings.nuextract_cloud_enabled,
            restart="api",
        ),
        _platform_field(
            key="nuextract_cloud_base_url",
            env_var="AUDIT_NUEXTRACT_CLOUD_BASE_URL",
            label="API base URL",
            description="NuExtract platform origin (default https://nuextract.ai).",
            value=settings.nuextract_cloud_base_url,
            restart="worker",
        ),
        _platform_field(
            key="nuextract_cloud_project_id",
            env_var="AUDIT_NUEXTRACT_CLOUD_PROJECT_ID",
            label="Project id (optional)",
            description="Fixed sprj_… project; omit to create a temp project per request.",
            value=settings.nuextract_cloud_project_id,
            restart="worker",
        ),
        _platform_field(
            key="nuextract_cloud_timeout_seconds",
            env_var="AUDIT_NUEXTRACT_CLOUD_TIMEOUT_SECONDS",
            label="Request timeout (s)",
            description="HTTP/SSE timeout for cloud jobs.",
            value=settings.nuextract_cloud_timeout_seconds,
            restart="worker",
        ),
        _platform_field(
            key="nuextract_cloud_api_key",
            env_var="AUDIT_NUEXTRACT_CLOUD_API_KEY",
            label="API key",
            description="Bearer token (stored as secret; not shown in full).",
            value="••••" if settings.nuextract_cloud_api_key else None,
            restart="worker",
        ),
    ]


def _qwen_stage_fields(settings: Settings) -> list[ModelConfigField]:
    """Text -> JSON stage shared by every OCR + Qwen catalog entry."""
    return [
        _platform_field(
            key="qwen35_base_url",
            env_var="AUDIT_QWEN35_BASE_URL",
            label="Qwen API base URL",
            description="OpenAI-compatible origin for text→JSON (default http://127.0.0.1:8084/v1).",
            value=settings.qwen35_base_url,
            restart="worker",
        ),
        _platform_field(
            key="qwen35_served_model",
            env_var="AUDIT_QWEN35_SERVED_MODEL",
            label="Qwen model id",
            description="llama-server model alias (default Qwen3.5-4B).",
            value=settings.qwen35_served_model,
            restart="worker",
        ),
        _platform_field(
            key="qwen35_timeout_seconds",
            env_var="AUDIT_QWEN35_TIMEOUT_SECONDS",
            label="Qwen request timeout (s)",
            description="HTTP timeout for text→JSON chat/completions.",
            value=settings.qwen35_timeout_seconds,
            restart="worker",
        ),
    ]


def _paddleocr_qwen_fields(settings: Settings) -> list[ModelConfigField]:
    return [
        _platform_field(
            key="paddleocr_qwen_enabled",
            env_var="AUDIT_PADDLEOCR_QWEN_ENABLED",
            label="Enabled",
            description="Register PP-OCRv6 + Qwen structured extraction in the catalog.",
            value=settings.paddleocr_qwen_enabled,
            restart="api",
        ),
        _platform_field(
            key="paddleocr_v6_base_url",
            env_var="AUDIT_PADDLEOCR_V6_BASE_URL",
            label="OCR API base URL",
            description="PaddleX OCR origin for the OCR stage (default http://127.0.0.1:8868).",
            value=settings.paddleocr_v6_base_url,
            restart="worker",
        ),
        *_qwen_stage_fields(settings),
    ]


def _glm_ocr_qwen_fields(settings: Settings) -> list[ModelConfigField]:
    return [
        _platform_field(
            key="glm_ocr_qwen_enabled",
            env_var="AUDIT_GLM_OCR_QWEN_ENABLED",
            label="Enabled",
            description="Register GLM-OCR + Qwen structured extraction in the catalog.",
            value=settings.glm_ocr_qwen_enabled,
            restart="api",
        ),
        _platform_field(
            key="glm_ocr_base_url",
            env_var="AUDIT_GLM_OCR_BASE_URL",
            label="GLM-OCR API base URL",
            description="llama-server /v1 origin for official SDK region OCR (default :8083/v1).",
            value=settings.glm_ocr_base_url,
            restart="worker",
        ),
        *_qwen_stage_fields(settings),
    ]


def _deployment_notes() -> list[DeploymentNote]:
    return [
        DeploymentNote(
            change_kind="Python / TypeScript code",
            action="Rebuild the affected image, then rollout",
            detail=(
                "Worker extraction logic, API routes, and benchmark scripts are baked into "
                "container images. Rebuild with pnpm images:build, then redeploy."
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
                "Local Repody VLM (repody:vlm) runs on host llama-server. "
                "Start with pnpm llamacpp:serve on the host."
            ),
        ),
        DeploymentNote(
            change_kind="NuExtract Cloud API",
            action="Set AUDIT_NUEXTRACT_CLOUD_* secrets, enable catalog, restart workers",
            detail=(
                "repody:vlm:cloud calls https://nuextract.ai with a bearer API key. "
                "No local GPU required."
            ),
        ),
        DeploymentNote(
            change_kind="PP-OCRv6 service",
            action="pnpm paddleocr:v6:serve, set AUDIT_PADDLEOCR_V6_*",
            detail=(
                "Internal PP-OCRv6 OCR stage (used by paddleocr:qwen): "
                "paddlex --serve --pipeline OCR (deploy/paddleocr-v6/OCR.yaml), "
                "client POST /ocr with Base64 file + fileType. "
                "See https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html"
            ),
        ),
        DeploymentNote(
            change_kind="PP-OCRv6 + Qwen structured extraction",
            action="pnpm paddleocr:v6:serve && pnpm qwen35:serve; set AUDIT_PADDLEOCR_QWEN_* and AUDIT_QWEN35_*",
            detail=(
                "paddleocr:qwen runs official POST /ocr then Qwen3.5 text→JSON. "
                "See deploy/qwen35/paths.local.env.example"
            ),
        ),
        DeploymentNote(
            change_kind="GLM-OCR (official SDK + llama-server)",
            action="uv sync --extra glmocr; pnpm glmocr:serve; set AUDIT_GLM_OCR_*",
            detail=(
                "Internal GLM-OCR stage (used by glm:qwen) defaults to whole-page "
                "Text Recognition: (no layout). "
                "Set AUDIT_GLM_OCR_LAYOUT_ENABLED=true for PP-DocLayoutV3. "
                "OCR hits llama-server :8083 (ggml-org/GLM-OCR-GGUF). "
                "See https://huggingface.co/zai-org/GLM-OCR"
            ),
        ),
        DeploymentNote(
            change_kind="GLM-OCR + Qwen structured extraction",
            action="pnpm glmocr:serve && pnpm qwen35:serve; set AUDIT_GLM_OCR_QWEN_ENABLED=true",
            detail=(
                "glm:qwen runs official GlmOcr SDK markdown then Qwen3.5 text→JSON "
                "(same schema prompt as paddleocr:qwen)."
            ),
        ),
    ]


def build_model_runtime_config(settings: Settings | None = None) -> ModelRuntimeConfigResponse:
    settings = settings or get_settings()
    # catalog id -> (field builder, inference URL, enabled flag)
    profile_sources = {
        REPODY_VLM_CATALOG_ID: (
            _repody_vlm_fields,
            settings.llamacpp_base_url,
            settings.repody_vlm_enabled,
        ),
        REPODY_VLM_CLOUD_CATALOG_ID: (
            _nuextract_cloud_fields,
            settings.nuextract_cloud_base_url,
            settings.nuextract_cloud_enabled,
        ),
        PADDLEOCR_QWEN_CATALOG_ID: (
            _paddleocr_qwen_fields,
            settings.qwen35_base_url,
            settings.paddleocr_qwen_enabled,
        ),
        GLM_OCR_QWEN_CATALOG_ID: (
            _glm_ocr_qwen_fields,
            settings.qwen35_base_url,
            settings.glm_ocr_qwen_enabled,
        ),
    }

    profiles: list[ModelRuntimeProfile] = []
    for spec in list_document_models():
        source = profile_sources.get(spec.id)
        render_policy = RENDER_POLICIES.get(spec.id)
        profiles.append(
            ModelRuntimeProfile(
                model_id=spec.id,
                label=spec.label,
                runtime=spec.runtime,
                runtime_model=spec.runtime_model,
                enabled=source is None or source[2] is not False,
                inference_url=source[1] if source else None,
                render_policy=render_policy.doc_ref if render_policy else "",
                fields=source[0](settings) if source else [],
            )
        )

    return ModelRuntimeConfigResponse(
        models=profiles,
        shared=_shared_fields(settings),
        deployment_notes=_deployment_notes(),
    )
