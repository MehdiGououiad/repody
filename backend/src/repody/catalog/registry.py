"""The document model: NuExtract3 on a local llama-server (``repody:vlm``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from repody.extraction.branding import (
    REPODY_VLM_CATALOG_ID,
    REPODY_VLM_DESCRIPTION,
    REPODY_VLM_LABEL,
)
from repody.extraction.modes import DEFAULT_READ_PATH_ID
from repody.extraction.types import DocumentBundle, ExtractionResult, SchemaFieldSpec
from repody.extraction.vlm import extract_with_repody_vlm
from repody.settings import Settings, get_settings

DocumentEngine = Literal["document_model"]
DocumentRuntime = Literal["llamacpp"]


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


def _spec(settings: Settings) -> DocumentModelSpec:
    return DocumentModelSpec(
        id=REPODY_VLM_CATALOG_ID,
        label=REPODY_VLM_LABEL,
        engine="document_model",
        runtime="llamacpp",
        runtime_model=settings.llamacpp_served_model,
        description=REPODY_VLM_DESCRIPTION,
    )


def normalize_model_id(model_id: str | None, *, settings: Settings | None = None) -> str:
    _ = (model_id, settings)
    return REPODY_VLM_CATALOG_ID


def parse_document_model(model_id: str | None) -> DocumentModelSpec:
    _ = model_id
    return _spec(get_settings())


def list_document_models() -> list[DocumentModelSpec]:
    settings = get_settings()
    return [_spec(settings)] if settings.repody_vlm_enabled else []


def is_markdown_only_model(model_id: str | None, *, settings: Settings | None = None) -> bool:
    _ = (model_id, settings)
    return False


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
    return await extract_with_repody_vlm(
        bundle,
        schema,
        document_type,
        spec=spec,
        extraction_instructions=extraction_instructions,
        markdown_extraction=markdown_extraction,
        extraction_icl_examples=extraction_icl_examples,
    )
