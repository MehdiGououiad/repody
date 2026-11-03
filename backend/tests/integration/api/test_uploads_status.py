"""Integration: upload confirm / multipath HTTP error matrix."""

from __future__ import annotations

import pytest
from tests.helpers.api_errors import assert_error_response


@pytest.mark.asyncio
async def test_confirm_upload_not_found(client):
    res = await client.post(
        "/v1/uploads/confirm",
        json={"storageKeys": ["runs/missing/doc.pdf"]},
    )
    assert_error_response(res, status_code=404, detail_contains="Upload not found")


@pytest.mark.asyncio
async def test_confirm_upload_rejects_empty_object(client):
    from repody.infra.storage.factory import get_storage

    storage = get_storage()
    key = "runs/empty/doc.pdf"
    await storage.put_bytes(key, b"", "application/pdf")

    res = await client.post("/v1/uploads/confirm", json={"storageKeys": [key]})
    assert_error_response(res, status_code=400, detail_contains="Upload empty")


@pytest.mark.asyncio
async def test_multipart_upload_returns_201(client):

    files = {"files": ("doc.pdf", b"%PDF-1.4\nsample", "application/pdf")}
    res = await client.post("/v1/uploads", files=files)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["uploads"][0]["storageKey"]
    assert body["uploads"][0]["size"] > 0


@pytest.mark.asyncio
async def test_upload_capabilities(client):
    res = await client.get("/v1/uploads/capabilities")
    assert res.status_code == 200
    body = res.json()
    assert body["uploadMode"] == "api"
    assert body["maxUploadBytes"] > 0
