"""extract_one must reach NuExtract through the real pipeline (no swallowed call errors)."""

from __future__ import annotations

import base64

import pytest
from tests.llm_mocks import disable_dmr_mock, enable_dmr_mock

from repody.agents.idp.adapters.extract import extract_one
from repody.agents.idp.contracts import DocumentSpec, SchemaField, StoredDocument

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.mark.asyncio
async def test_extract_one_runs_pipeline_against_inference(monkeypatch):
    router = enable_dmr_mock(monkeypatch)
    try:
        result = await extract_one(
            DocumentSpec(
                id="d1", label="Invoice", schema_fields=(SchemaField(name="total_amount"),)
            ),
            StoredDocument(
                document_id="d1", storage_key="k", mime_type="image/png", size_bytes=len(PNG_1X1)
            ),
            PNG_1X1,
        )
    finally:
        disable_dmr_mock(router)
    assert result.ok, result.error
    assert result.value is not None
    # The mocked NuExtract answers 6000.00; a schema-only placeholder would be empty.
    assert [(f.key, f.value) for f in result.value.fields] == [("total_amount", "6000.00")]
