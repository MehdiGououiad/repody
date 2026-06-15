"""Comprehensive in-process API E2E suite (Hatchet dispatch simulated in conftest)."""

from __future__ import annotations

import json
import uuid

import pytest

from audit_workbench.extraction.model_registry import REPODY_VLM_CATALOG_ID
from tests.test_e2e.facture_helpers import (
    EXPECTED_TOTAL,
    FACTURE_PDF,
    FACTURE_UI_PATHS,
    LOGIC_RULE_TOTAL_OK,
    WORKFLOW_NAME,
    document_def,
    facture_bytes,
    rules_for_case,
    total_from_result,
)

TEXT_LAYER_CASE = FACTURE_UI_PATHS[0]


@pytest.mark.asyncio
async def test_healthz_reports_hatchet(client):
    res = await client.get("/v1/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["queueBackend"] == "hatchet"
    assert "workerPools" in body
    assert body["workerPools"]["fast"] == "fast"
    assert body["workerPools"]["ocr"] == "ocr"


@pytest.mark.asyncio
async def test_upload_capabilities(client):
    res = await client.get("/v1/uploads/capabilities")
    assert res.status_code == 200
    body = res.json()
    assert body["storageBackend"] in ("local", "s3")


@pytest.mark.asyncio
async def test_processing_paths_catalog(client):
    res = await client.get("/v1/processing-paths")
    assert res.status_code == 200
    paths = res.json()["paths"]
    ids = {p["id"] for p in paths}
    assert "document_model" in ids


@pytest.mark.asyncio
async def test_ocr_model_catalog_reports_runtime_availability(client, monkeypatch):
    from audit_workbench.settings import get_settings

    settings = get_settings()
    async def fake_installed_runtime_models(_settings=None):
        return {
            "docker_model_runner": {settings.repody_vlm_model.lower()},
            "vllm": set(),
        }

    monkeypatch.setattr(
        "audit_workbench.services.document_model_catalog.installed_runtime_models",
        fake_installed_runtime_models,
    )

    response = await client.get("/v1/ocr/models")

    assert response.status_code == 200
    models = {model["id"]: model for model in response.json()["models"]}
    assert models[REPODY_VLM_CATALOG_ID]["available"] is True
    assert models[REPODY_VLM_CATALOG_ID]["runtime"] == "Repody VLM"


@pytest.mark.asyncio
async def test_workflow_lifecycle(client):
    suffix = uuid.uuid4().hex[:8]
    wf_id = f"wf-api-e2e-{suffix}"
    doc_id = f"doc-{suffix}"
    field_id = f"f-{suffix}"

    created = await client.put(
        f"/v1/workflows/{wf_id}",
        json={
            "id": wf_id,
            "name": "API E2E Workflow",
            "description": "lifecycle",
            "status": "draft",
            "owner": "pytest",
            "documents": [
                {
                    "id": doc_id,
                    "documentType": "Invoice",
                    "schema": [{"id": field_id, "name": "total_amount", "description": "Total"}],
                }
            ],
            "rules": [
                {
                    "id": f"rule-{suffix}",
                    "name": "Positive total",
                    "kind": "logic",
                    "scope": "intra",
                    "appliesTo": [doc_id],
                    "body": "total_amount > 0",
                    "severity": "reject",
                }
            ],
        },
    )
    assert created.status_code == 200

    listed = await client.get("/v1/workflows")
    assert listed.status_code == 200
    assert any(w["id"] == wf_id for w in listed.json()["workflows"])

    deployed = await client.post(f"/v1/workflows/{wf_id}/deploy", json={})
    assert deployed.status_code == 200
    assert deployed.json()["workflow"]["deployedAt"]
    api_key = deployed.json()["workflow"]["apiKey"]
    assert api_key

    unauthorized = await client.post(f"/v1/workflows/{wf_id}/run")
    assert unauthorized.status_code == 401

    started = await client.post(
        f"/v1/workflows/{wf_id}/run",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    poll = await client.get(f"/v1/runs/{run_id}")
    assert poll.status_code == 200
    body = poll.json()
    assert body["status"] in ("done", "failed", "queued", "running")
    if body["status"] == "failed":
        pytest.fail(body.get("error") or "run failed")


@pytest.mark.asyncio
async def test_run_status_lightweight_poll(client):
    res = await client.post(
        "/v1/workflows/wf-invoice-audit/runs/json?mode=test",
        json={
            "snapshot": {
                "documents": [],
                "rules": [],
                "workflowName": "Invoice Audit Pipeline",
            }
        },
    )
    assert res.status_code == 202
    run_id = res.json()["runId"]

    status = await client.get(f"/v1/runs/{run_id}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] in ("done", "failed", "warning", "passed", "queued", "running")
    assert body.get("progress") is not None or body["status"] == "done"


@pytest.mark.asyncio
async def test_run_events_sse_smoke(client):
    res = await client.post(
        "/v1/workflows/wf-invoice-audit/runs/json?mode=test",
        json={
            "snapshot": {
                "documents": [],
                "rules": [],
                "workflowName": "Invoice Audit Pipeline",
            }
        },
    )
    assert res.status_code == 202
    run_id = res.json()["runId"]

    async with client.stream("GET", f"/v1/runs/{run_id}/events", timeout=10.0) as stream:
        assert stream.status_code == 200
        first = b""
        async for part in stream.aiter_bytes():
            first += part
            if len(first) >= 64 or b"data:" in first:
                break
        assert b"data:" in first


@pytest.mark.asyncio
async def test_multipart_test_run_with_facture(client, mock_ollama_llm):
    if not FACTURE_PDF.is_file():
        pytest.skip("Facture.pdf fixture not found")

    suffix = uuid.uuid4().hex[:8]
    wf_id = f"wf-facture-api-{suffix}"
    doc_id = f"doc-facture-{suffix}"
    pdf = facture_bytes()

    saved = await client.put(
        f"/v1/workflows/{wf_id}",
        json={
            "id": wf_id,
            "name": WORKFLOW_NAME,
            "description": "facture api e2e",
            "status": "draft",
            "owner": "pytest",
            "documents": [document_def(TEXT_LAYER_CASE, doc_id=doc_id)],
            "rules": rules_for_case(TEXT_LAYER_CASE),
        },
    )
    assert saved.status_code == 200

    payload = json.dumps(
        {
            "documents": [document_def(TEXT_LAYER_CASE, doc_id=doc_id)],
            "rules": rules_for_case(TEXT_LAYER_CASE),
            "workflowName": WORKFLOW_NAME,
        }
    )
    started = await client.post(
        f"/v1/workflows/{wf_id}/runs?mode=test",
        files=[
            ("payload", (None, payload.encode(), "application/json")),
            ("document_ids", (None, json.dumps([doc_id]).encode(), "application/json")),
            ("files", ("Facture.pdf", pdf, "application/pdf")),
        ],
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    from tests.test_e2e.ui_flow import poll_run_until_done

    result = await poll_run_until_done(client, run_id, max_ms=120_000)
    assert total_from_result(result) == EXPECTED_TOTAL


@pytest.mark.asyncio
async def test_audits_and_metrics_endpoints(client):
    metrics = await client.get("/v1/metrics")
    assert metrics.status_code == 200
    assert "kpis" in metrics.json()

    audits = await client.get("/v1/audits")
    assert audits.status_code == 200
    assert isinstance(audits.json()["audits"], list)

    rules = await client.get("/v1/rules/library")
    assert rules.status_code == 200
    assert len(rules.json()["rules"]) >= 1

    dry = await client.post(
        "/v1/workflows/wf-invoice-audit/dry-run",
        json={
            "fields": [{"id": "1", "name": "subtotal", "description": ""}],
            "rules": [
                {
                    "id": "r1",
                    "name": "Math",
                    "kind": "logic",
                    "body": "subtotal + tax == total_amount",
                    "severity": "reject",
                }
            ],
        },
    )
    assert dry.status_code == 200
    assert dry.json()["ruleResults"][0]["status"] in ("failed", "skipped")
