"""Platform config and diagnostics API schemas."""

from __future__ import annotations

from pydantic import Field

from audit_workbench.schemas.common import CamelModel


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
    worker_task_timeout_minutes: int = Field(serialization_alias="workerTaskTimeoutMinutes")
    maintenance_interval_seconds: int = Field(serialization_alias="maintenanceIntervalSeconds")
    worker_pools: dict[str, str] = Field(default_factory=dict, serialization_alias="workerPools")
    taskiq_configured: bool = Field(default=False, serialization_alias="taskiqConfigured")
    llm_validation_enabled: bool = Field(default=False, serialization_alias="llmValidationEnabled")
    gpu_live_probe: bool = Field(default=False, serialization_alias="gpuLiveProbe")
    healthz_probe_inference: bool = Field(
        default=False, serialization_alias="healthzProbeInference"
    )


class OcrDiagnosticSettingsSchema(CamelModel):
    extractor: str = ""
    inference_mode: str = Field(default="", serialization_alias="inferenceMode")
    runtime: str = ""
    document_model_pdf_dpi: int = Field(default=0, serialization_alias="documentModelPdfDpi")
    document_model_max_edge_px: int | None = Field(
        default=None, serialization_alias="documentModelMaxEdgePx"
    )
    llm_validation_enabled: bool = Field(default=False, serialization_alias="llmValidationEnabled")


class OcrDiagnosticResponse(CamelModel):
    ok: bool
    model: str
    runtime: str = ""
    inference_reachable: bool = False
    model_in_registry: bool = False
    model_loaded: bool = False
    extractor: str = ""
    inference_mode: str = ""
    infer_ms: int | None = None
    sample_extracted: bool = False
    detail: str = ""
    hint: str = ""
    settings: OcrDiagnosticSettingsSchema = Field(default_factory=OcrDiagnosticSettingsSchema)


class SuggestTemplateTypeResponse(CamelModel):
    template_type: str = Field(serialization_alias="templateType")
