"""The document model catalog: one NuExtract model plus live llama-server status."""

from __future__ import annotations

import pytest

from repody.catalog import api as catalog_api
from repody.catalog.registry import normalize_model_id, parse_document_model
from repody.catalog.status import ModelStatus
from repody.extraction.branding import REPODY_VLM_CATALOG_ID


def test_every_stored_model_id_resolves_to_nuextract():
    for stored in (None, "", REPODY_VLM_CATALOG_ID, "paddleocr:qwen", "glm:qwen"):
        assert normalize_model_id(stored) == REPODY_VLM_CATALOG_ID
    assert parse_document_model("repody:vlm:cloud").id == REPODY_VLM_CATALOG_ID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "available", "note_fragment"),
    [
        (ModelStatus(reachable=True, loaded=True), True, None),
        (ModelStatus(reachable=True, loaded=False), False, "does not serve"),
        (ModelStatus(reachable=False, loaded=False), False, "not reachable"),
    ],
)
async def test_catalog_reports_model_status(monkeypatch, status, available, note_fragment):
    async def fake_status(_settings=None):
        return status

    monkeypatch.setattr(catalog_api, "model_status", fake_status)
    catalog = await catalog_api.fetch_models_catalog()
    (entry,) = catalog.models
    assert entry.id == REPODY_VLM_CATALOG_ID
    assert entry.available is available
    if note_fragment is None:
        assert entry.availability_note is None
    else:
        assert note_fragment in (entry.availability_note or "")
