"""Pluggable document model registry.

Each catalog id maps to a runtime and extraction adapter module:
- ``repody_vlm`` — NuExtract structured extraction + markdown

Render policies: ``extraction/document_render.py``
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
    UnknownCatalogIdError,
    normalize_public_catalog_id,
)
from audit_workbench.inference.runtime import default_document_runtime
from audit_workbench.settings import Settings, get_settings

DocumentEngine = Literal["document_model"]
DocumentRuntime = Literal["docker_model_runner", "vllm"]

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
    normalized = normalize_model_id(model_id, settings=settings)
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
) -> ExtractionResult:
    from audit_workbench.catalog.adapters import get_document_model_adapter

    adapter = get_document_model_adapter(spec.id)
    if adapter is not None:
        return await adapter(
            bundle,
            schema,
            document_type,
            spec=spec,
            extraction_instructions=extraction_instructions,
            markdown_extraction=markdown_extraction,
        )
    if spec.engine != "document_model":
        raise RuntimeError(f"Unsupported document model engine: {spec.engine} ({spec.id})")
    raise RuntimeError(f"Unsupported document model handler: {spec.id} ({spec.runtime})")
