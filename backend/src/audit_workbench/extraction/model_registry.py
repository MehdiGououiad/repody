"""Pluggable document model registry.

Each catalog id maps to a runtime and extraction adapter module:
- ``repody_vlm`` — NuExtract structured extraction + markdown
- ``surya_ocr`` — Surya OCR 2 benchmark compare

Render policies: ``extraction/document_render.py``
Inference env: ``extraction/model_inference_env.py`` (Surya)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from audit_workbench.extraction.base import ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.document_model_branding import (
    REPODY_VLM_CATALOG_ID,
    REPODY_VLM_DESCRIPTION,
    REPODY_VLM_LABEL,
    SURYA_OCR2_CATALOG_ID,
    SURYA_OCR2_DESCRIPTION,
    SURYA_OCR2_LABEL,
    is_legacy_catalog_id,
    normalize_public_catalog_id,
)
from audit_workbench.extraction.repody_vlm import extract_with_repody_vlm
from audit_workbench.inference.runtime import default_document_runtime
from audit_workbench.settings import Settings, get_settings

DocumentEngine = Literal["document_model", "ocr_compare"]
DocumentRuntime = Literal["docker_model_runner", "vllm", "surya"]

DEFAULT_READ_PATH_ID = "document_model"


@dataclass(frozen=True)
class DocumentModelSpec:
    """Catalog entry for a structured document extraction model."""

    id: str
    label: str
    engine: DocumentEngine
    runtime: DocumentRuntime
    runtime_model: str
    read_path_id: str = DEFAULT_READ_PATH_ID
    description: str = ""
    compare_only: bool = False
    workflow_selectable: bool = False
    markdown_only: bool = False


def _runtime_model_for(settings: Settings, runtime: DocumentRuntime) -> str:
    if runtime == "vllm":
        return settings.vllm_served_model
    return settings.repody_vlm_model


def _registered_models(settings: Settings) -> dict[str, DocumentModelSpec]:
    models: dict[str, DocumentModelSpec] = {}
    if settings.repody_vlm_enabled:
        runtime: DocumentRuntime = default_document_runtime(settings)  # type: ignore[assignment]
        models[REPODY_VLM_CATALOG_ID] = DocumentModelSpec(
            id=REPODY_VLM_CATALOG_ID,
            label=REPODY_VLM_LABEL,
            engine="document_model",
            runtime=runtime,
            runtime_model=_runtime_model_for(settings, runtime),
            description=REPODY_VLM_DESCRIPTION,
        )
    if settings.surya_ocr_enabled:
        models[SURYA_OCR2_CATALOG_ID] = DocumentModelSpec(
            id=SURYA_OCR2_CATALOG_ID,
            label=SURYA_OCR2_LABEL,
            engine="ocr_compare",
            runtime="surya",
            runtime_model="datalab-to/surya-ocr-2",
            description=SURYA_OCR2_DESCRIPTION,
            compare_only=True,
            workflow_selectable=True,
            markdown_only=True,
        )
    return models


def normalize_model_id(model_id: str | None, *, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    raw = (model_id or settings.default_ocr_model or REPODY_VLM_CATALOG_ID).strip()
    if not raw:
        return _default_catalog_id(settings)
    normalized = normalize_public_catalog_id(raw)
    registry = _registered_models(settings)
    if normalized in registry:
        return normalized
    if is_legacy_catalog_id(raw) and settings.repody_vlm_enabled:
        return REPODY_VLM_CATALOG_ID
    if settings.default_ocr_model in registry:
        return normalize_public_catalog_id(settings.default_ocr_model)
    return _default_catalog_id(settings)


def _default_catalog_id(settings: Settings) -> str:
    registry = _registered_models(settings)
    if REPODY_VLM_CATALOG_ID in registry:
        return REPODY_VLM_CATALOG_ID
    if registry:
        return next(iter(registry.keys()))
    raise RuntimeError("No document models are enabled.")


def parse_document_model(model_id: str | None) -> DocumentModelSpec:
    settings = get_settings()
    registry = _registered_models(settings)
    normalized = normalize_model_id(model_id, settings=settings)
    spec = registry.get(normalized)
    if spec is not None:
        return spec
    if registry:
        return next(iter(registry.values()))
    raise RuntimeError("No document models are enabled. Enable Repody VLM.")


def list_document_models() -> list[DocumentModelSpec]:
    return list(_registered_models(get_settings()).values())


def is_markdown_only_model(model_id: str | None, *, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    normalized = normalize_model_id(model_id, settings=settings)
    spec = _registered_models(settings).get(normalized)
    return bool(spec and spec.markdown_only)


def is_ocr_compare_model(model_id: str | None, *, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    normalized = normalize_model_id(model_id, settings=settings)
    spec = _registered_models(settings).get(normalized)
    return bool(spec and spec.compare_only)


async def extract_with_document_model(
    spec: DocumentModelSpec,
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
) -> ExtractionResult:
    if spec.id == REPODY_VLM_CATALOG_ID or is_legacy_catalog_id(spec.id):
        return await extract_with_repody_vlm(
            bundle,
            schema,
            document_type,
            spec=spec,
            extraction_instructions=extraction_instructions,
            markdown_extraction=markdown_extraction,
        )
    if spec.id == SURYA_OCR2_CATALOG_ID:
        from audit_workbench.extraction.surya_ocr import extract_with_surya_ocr2

        return await extract_with_surya_ocr2(
            bundle,
            schema,
            document_type,
            markdown_extraction=markdown_extraction or spec.markdown_only,
        )
    if spec.engine != "document_model":
        raise RuntimeError(f"Unsupported document model engine: {spec.engine} ({spec.id})")
    raise RuntimeError(f"Unsupported document model handler: {spec.id} ({spec.runtime})")
