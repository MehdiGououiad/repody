from __future__ import annotations

import json

import pytest

from audit_workbench.settings import get_settings


@pytest.mark.asyncio
async def test_operator_status_is_available_in_read_only_mode(client):
    response = await client.get("/v1/operator/status")

    assert response.status_code == 200
    body = response.json()
    assert body["actionsEnabled"] is False
    assert body["limits"]["maxUploadBytes"] > 0


@pytest.mark.asyncio
async def test_operator_actions_are_gated_by_default(client):
    response = await client.post(
        "/v1/operator/models/pull",
        json={"model": "repody/repody-vlm:q4_k_m-16k"},
    )

    assert response.status_code == 403
    assert "AUDIT_OPERATOR_ACTIONS_ENABLED" in response.json()["detail"]


@pytest.mark.asyncio
async def test_benchmark_rejects_invalid_manifest(client, monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_OPERATOR_ACTIONS_ENABLED", "true")
    monkeypatch.setenv("AUDIT_OPERATOR_DATA_PATH", str(tmp_path))
    get_settings.cache_clear()

    response = await client.post(
        "/v1/operator/benchmarks",
        data={
            "profile": "models",
            "models": json.dumps(["repody:vlm"]),
        },
        files={
            "document": ("invoice.pdf", b"%PDF-1.4\n%%EOF", "application/pdf"),
            "manifest": ("manifest.json", b"{bad-json", "application/json"),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Benchmark manifest must be valid JSON."


@pytest.mark.asyncio
async def test_benchmark_rejects_unsafe_model_identifier(client, monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_OPERATOR_ACTIONS_ENABLED", "true")
    monkeypatch.setenv("AUDIT_OPERATOR_DATA_PATH", str(tmp_path))
    get_settings.cache_clear()

    response = await client.post(
        "/v1/operator/benchmarks",
        data={
            "profile": "models",
            "models": json.dumps(["model; rm -rf /"]),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid model identifier."
