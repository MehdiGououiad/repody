"""Pluggable document model registry.

Each catalog id maps to a runtime and extraction adapter module:
- ``repody:vlm`` — local llama.cpp NuExtract structured extraction
- ``repody:vlm:cloud`` — official NuExtract platform REST API
- ``paddleocr:qwen`` — PP-OCRv6 OCR + Qwen3.5 text→JSON structured extraction
- ``glm:qwen`` — GLM-OCR SDK markdown + Qwen3.5 text→JSON structured extraction

Markdown-only engines (``paddleocr:v6``, ``glm:ocr``) are adapter internals for the
Qwen stages — they are not workflow-selectable catalog entries.

Render policies: ``extraction/render.py``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from repody.extraction.branding import (
    GLM_OCR_QWEN_CATALOG_ID,
    GLM_OCR_QWEN_DESCRIPTION,
    GLM_OCR_QWEN_LABEL,
    PADDLEOCR_QWEN_CATALOG_ID,
    PADDLEOCR_QWEN_DESCRIPTION,
    PADDLEOCR_QWEN_LABEL,
    REPODY_VLM_CATALOG_ID,
    REPODY_VLM_CLOUD_CATALOG_ID,
    REPODY_VLM_CLOUD_DESCRIPTION,
    REPODY_VLM_CLOUD_LABEL,
    REPODY_VLM_DESCRIPTION,
    REPODY_VLM_LABEL,
    UnknownCatalogIdError,
    normalize_public_catalog_id,
)
from repody.extraction.modes import DEFAULT_READ_PATH_ID
from repody.extraction.types import (
    DocumentBundle,
    ExtractionResult,
    SchemaFieldSpec,
)
from repody.inference.runtime import (
    DOCUMENT_RUNTIME,
    GLM_OCR_QWEN_RUNTIME,
    NUEXTRACT_CLOUD_RUNTIME,
    PADDLEOCR_QWEN_RUNTIME,
)
from repody.settings import Settings, get_settings

DocumentEngine = Literal["document_model"]
DocumentRuntime = Literal[
    "llamacpp",
    "nuextract_cloud",
    "paddleocr_qwen",
    "glm_ocr_qwen",
]


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
    workflow_selectable: bool = True
    markdown_only: bool = False


def _runtime_model_for(settings: Settings) -> str:
    return settings.llamacpp_served_model


def _registered_models(settings: Settings) -> dict[str, DocumentModelSpec]:
    models: dict[str, DocumentModelSpec] = {}
    if settings.repody_vlm_enabled:
        models[REPODY_VLM_CATALOG_ID] = DocumentModelSpec(
            id=REPODY_VLM_CATALOG_ID,
            label=REPODY_VLM_LABEL,
            engine="document_model",
            runtime=DOCUMENT_RUNTIME,
            runtime_model=_runtime_model_for(settings),
            description=REPODY_VLM_DESCRIPTION,
            workflow_selectable=True,
        )
    if settings.nuextract_cloud_enabled:
        models[REPODY_VLM_CLOUD_CATALOG_ID] = DocumentModelSpec(
            id=REPODY_VLM_CLOUD_CATALOG_ID,
            label=REPODY_VLM_CLOUD_LABEL,
            engine="document_model",
            runtime=NUEXTRACT_CLOUD_RUNTIME,
            runtime_model="nuextract-cloud",
            description=REPODY_VLM_CLOUD_DESCRIPTION,
            workflow_selectable=True,
        )
    if settings.paddleocr_qwen_enabled:
        models[PADDLEOCR_QWEN_CATALOG_ID] = DocumentModelSpec(
            id=PADDLEOCR_QWEN_CATALOG_ID,
            label=PADDLEOCR_QWEN_LABEL,
            engine="document_model",
            runtime=PADDLEOCR_QWEN_RUNTIME,
            runtime_model=settings.qwen35_served_model,
            description=PADDLEOCR_QWEN_DESCRIPTION,
            workflow_selectable=True,
            markdown_only=False,
        )
    if settings.glm_ocr_qwen_enabled:
        models[GLM_OCR_QWEN_CATALOG_ID] = DocumentModelSpec(
            id=GLM_OCR_QWEN_CATALOG_ID,
            label=GLM_OCR_QWEN_LABEL,
            engine="document_model",
            runtime=GLM_OCR_QWEN_RUNTIME,
            runtime_model=settings.qwen35_served_model,
            description=GLM_OCR_QWEN_DESCRIPTION,
            workflow_selectable=True,
            markdown_only=False,
        )
    return models


def normalize_model_id(model_id: str | None, *, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    raw = (model_id or settings.default_document_model_id or REPODY_VLM_CATALOG_ID).strip()
    if not raw:
        return _default_catalog_id(settings)
    normalized = normalize_public_catalog_id(raw)
    registry = _registered_models(settings)
    if normalized in registry:
        return normalized
    raise UnknownCatalogIdError(
        f"Document model {normalized!r} is not registered. "
        f"Available: {', '.join(sorted(registry)) or '(none)'}"
    )


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
    raise UnknownCatalogIdError(f"Document model {normalized!r} is not registered.")


def list_document_models() -> list[DocumentModelSpec]:
    return list(_registered_models(get_settings()).values())


def is_markdown_only_model(model_id: str | None, *, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    try:
        normalized = normalize_model_id(model_id, settings=settings)
    except UnknownCatalogIdError:
        return False
    spec = _registered_models(settings).get(normalized)
    return bool(spec and spec.markdown_only)


async def extract_with_document_model(
    spec: DocumentModelSpec,
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list | None = None,
) -> ExtractionResult:
    from repody.catalog.adapters import get_document_model_adapter

    adapter = get_document_model_adapter(spec.id)
    if adapter is not None:
        return await adapter(
            bundle,
            schema,
            document_type,
            spec=spec,
            extraction_instructions=extraction_instructions,
            markdown_extraction=markdown_extraction or spec.markdown_only,
            extraction_icl_examples=extraction_icl_examples,
        )
    if spec.engine != "document_model":
        raise RuntimeError(f"Unsupported document model engine: {spec.engine} ({spec.id})")
    raise RuntimeError(f"Unsupported document model handler: {spec.id} ({spec.runtime})")
