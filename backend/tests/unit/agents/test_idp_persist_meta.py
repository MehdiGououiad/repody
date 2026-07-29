"""IDP persist uses the shared ExtractionMetadata → meta_to_dict wire shape."""

from __future__ import annotations

import pytest

from repody.agents.idp.adapters.mapping import document_extraction_from_result
from repody.agents.idp.adapters.persist import extraction_meta_to_dict
from repody.agents.idp.contracts import DocumentExtraction, ExtractedField
from repody.extraction.types import (
    ExtractedFieldResult,
    ExtractionMetadata,
    ExtractionResult,
)
from repody.schemas.run import RunDocumentExtractionMeta


def _full_meta(**overrides) -> ExtractionMetadata:
    base = dict(
        read_path_config="document_model",
        read_path_used="document_model",
        read_path_label="NuExtract vision",
        validation_mode="logic_only",
        validation_label="Logic rules",
        document_model_id="repody:vlm:cloud",
        extraction_ms=7000,
        cache_hit=False,
        fields_extracted=1,
    )
    base.update(overrides)
    return ExtractionMetadata(**base)


def test_extraction_meta_to_dict_matches_api_schema() -> None:
    doc = DocumentExtraction(
        document_id="d1",
        fields=(
            ExtractedField(
                key="full_name",
                value="ACHRAF MAHIR",
                field_type="string",
                extracted=True,
                confidence=0.95,
            ),
        ),
        markdown_text=None,
        meta=_full_meta(),
    )
    raw = extraction_meta_to_dict(doc)
    meta = RunDocumentExtractionMeta.model_validate(raw)
    assert meta.read_path_config == "document_model"
    assert meta.validation_mode == "logic_only"
    assert meta.document_model_id == "repody:vlm:cloud"
    assert meta.fields_extracted == 1


def test_document_extraction_from_result_requires_meta() -> None:
    with pytest.raises(ValueError, match="meta is required"):
        document_extraction_from_result(
            document_id="d1",
            result=ExtractionResult(fields=[]),
        )


def test_document_extraction_from_result_passes_pipeline_meta() -> None:
    pipeline_meta = _full_meta(document_model_id="repody:vlm:cloud")
    mapped = document_extraction_from_result(
        document_id="d1",
        result=ExtractionResult(
            fields=[
                ExtractedFieldResult(
                    key="full_name",
                    description="",
                    value="ACHRAF MAHIR",
                    type="string",
                    confidence=0.9,
                    extracted=True,
                )
            ],
            meta=pipeline_meta,
        ),
    )
    assert mapped.meta is pipeline_meta
    RunDocumentExtractionMeta.model_validate(extraction_meta_to_dict(mapped))
