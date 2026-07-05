"""In-process API tests (no Taskiq workers). Run-completion flows use @pytest.mark.live + live_client."""

from __future__ import annotations

import json
import uuid

import pytest

from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID
from tests.helpers.workflow_rules import logic_field_gt
from audit_workbench.integration.facture import (
    EXPECTED_TOTAL,
    FACTURE_PDF,
    FACTURE_UI_PATHS,
    WORKFLOW_NAME,
    document_def,
    facture_bytes,
    rules_for_case,
    total_from_result,
)

TEXT_LAYER_CASE = FACTURE_UI_PATHS[0]


@pytest.mark.asyncio
async def test_platform_config(client):
    res = await client.get("/v1/platform/config")
    assert res.status_code == 200
    body = res.json()
    assert "extractor" in body
    assert "queueBackend" in body
    assert "maxUploadBytes" in body


@pytest.mark.asyncio
async def test_model_runtime_config(client):
    res = await client.get("/v1/platform/model-runtime-config")
    assert res.status_code == 200
    body = res.json()
    assert "models" in body
    assert "deploymentNotes" in body
    assert any(m["modelId"] == REPODY_VLM_CATALOG_ID for m in body["models"])


@pytest.mark.asyncio
async def test_healthz_reports_configured_queue_backend(client):
    res = await client.get("/v1/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["redisOk"] is True
    assert body["queueBackend"] == "taskiq"
    assert "workerPools" in body
    assert body["workerPools"]["fast"] == "fast"
    assert body["workerPools"]["extract"] == "extract"


@pytest.mark.asyncio
async def test_upload_capabilities(client):
    res = await client.get("/v1/uploads/capabilities")
    assert res.status_code == 200
    body = res.json()
    assert body["storageBackend"] in ("local", "s3")


@pytest.mark.asyncio
async def test_models_catalog_includes_processing_paths(client):
    res = await client.get("/v1/models/catalog")
    assert res.status_code == 200
    body = res.json()
    paths = body["paths"]
    ids = {p["id"] for p in paths}
    assert "document_model" in ids
    assert body["defaultPath"] == "document_model"
    assert any(v["id"] == "logic_only" for v in body["validationModes"])
    assert not any(v["id"] == "logic_and_llm" for v in body["validationModes"])


@pytest.mark.asyncio
async def test_document_model_id_catalog_reports_runtime_availability(client, monkeypatch):
    from audit_workbench.settings import get_settings

    settings = get_settings()

    async def fake_installed_runtime_models(_settings=None):
        return {
            "docker_model_runner": {settings.repody_vlm_model.lower()},
            "vllm": set(),
        }

    monkeypatch.setattr(
        "audit_workbench.catalog.probes.installed_runtime_models",
        fake_installed_runtime_models,
    )

    response = await client.get("/v1/models/catalog")

    assert response.status_code == 200
    models = {model["id"]: model for model in response.json()["models"]}
    assert models[REPODY_VLM_CATALOG_ID]["available"] is True
    assert models[REPODY_VLM_CATALOG_ID]["runtime"] == "Repody VLM"


@pytest.mark.asyncio
async def test_workflow_lifecycle_deploy_and_auth(client):
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
                    "schema": [
                        {
                            "id": field_id,
                            "name": "total_amount",
                            "description": "Total",
                            "templateType": "number",
                        }
                    ],
                }
            ],
            "rules": [
                logic_field_gt(
                    rule_id=f"rule-{suffix}",
                    name="Positive total",
                    doc_id=doc_id,
                    field="total_amount",
                    value="0",
                )
            ],
        },
    )
    assert created.status_code == 200

    listed = await client.get("/v1/workflows")
    assert listed.status_code == 200
    assert any(w["id"] == wf_id for w in listed.json()["workflows"])
    loaded = await client.get(f"/v1/workflows/{wf_id}")
    assert loaded.status_code == 200
    assert loaded.json()["workflow"]["documents"][0]["schema"][0]["templateType"] == "number"

    deployed = await client.post(f"/v1/workflows/{wf_id}/deploy", json={})
    assert deployed.status_code == 200
    assert deployed.json()["workflow"]["deployedAt"]
    api_key = deployed.json()["workflow"]["apiKey"]
    assert api_key

    unauthorized = await client.post(f"/v1/workflows/{wf_id}/runs")
    assert unauthorized.status_code == 401


@pytest.mark.asyncio
async def test_enqueue_without_worker_returns_queued(client):
    """Enqueue commits the run + outbox before background Taskiq dispatch."""
    res = await client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
        json={
            "snapshot": {
                "documents": [],
                "rules": [],
                "workflowName": "Invoice Audit Pipeline",
            }
        },
    )
    assert res.status_code == 202
    body = res.json()
    assert body["runId"]
    assert body["status"] == "queued"


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


@pytest.mark.asyncio
async def test_seed_workflow_cannot_be_archived(client):
    res = await client.delete("/v1/workflows/wf-invoice-audit")
    assert res.status_code == 404
    detail = await client.get("/v1/workflows/wf-invoice-audit")
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_workflow_put_create_and_post_put_upsert(client):
    wf_id = "wf-put-create-e2e"
    doc_id = "doc-put-create-e2e"
    field_id = "f-put-create-e2e"
    payload = {
        "id": wf_id,
        "name": "PUT create",
        "description": "",
        "status": "draft",
        "owner": "Tester",
        "documents": [
            {
                "id": doc_id,
                "documentType": "Invoice",
                "schema": [{"id": field_id, "name": "total_amount", "description": "Total"}],
            }
        ],
        "rules": [],
    }
    created = await client.put(f"/v1/workflows/{wf_id}", json=payload)
    assert created.status_code == 200
    assert created.json()["workflow"]["id"] == wf_id

    post = await client.post(
        "/v1/workflows",
        json={"name": "POST sibling", "description": "", "owner": "Tester"},
    )
    assert post.status_code == 201
    assert post.json()["workflow"]["id"] != wf_id

    upsert = await client.put(
        f"/v1/workflows/{wf_id}",
        json={**payload, "name": "PUT updated"},
    )
    assert upsert.status_code == 200
    assert upsert.json()["workflow"]["name"] == "PUT updated"


from audit_workbench.db.seed import SEED_API_KEY


@pytest.mark.asyncio
async def test_api_run_requires_seed_key(client):
    res = await client.post("/v1/workflows/wf-invoice-audit/runs")
    assert res.status_code == 401


# --- Live stack (Taskiq workers) ---


@pytest.mark.live
@pytest.mark.asyncio
async def test_workflow_lifecycle_api_run(live_client):
    suffix = uuid.uuid4().hex[:8]
    wf_id = f"wf-api-live-{suffix}"
    doc_id = f"doc-{suffix}"

    created = await live_client.put(
        f"/v1/workflows/{wf_id}",
        json={
            "id": wf_id,
            "name": "API live workflow",
            "description": "",
            "status": "draft",
            "owner": "pytest",
            "documents": [
                {
                    "id": doc_id,
                    "documentType": "Invoice",
                    "schema": [{"id": "f1", "name": "total_amount", "description": "Total"}],
                }
            ],
            "rules": [],
        },
    )
    assert created.status_code == 200

    deployed = await live_client.post(f"/v1/workflows/{wf_id}/deploy", json={})
    assert deployed.status_code == 200
    api_key = deployed.json()["workflow"]["apiKey"]

    started = await live_client.post(
        f"/v1/workflows/{wf_id}/runs",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    poll = await live_client.get(f"/v1/runs/{run_id}")
    assert poll.status_code == 200
    body = poll.json()
    assert body["status"] in ("done", "failed", "queued", "running")
    if body["status"] == "failed":
        pytest.fail(body.get("error") or "run failed")


@pytest.mark.live
@pytest.mark.asyncio
async def test_run_status_lightweight_poll(live_client):
    res = await live_client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
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

    status = await live_client.get(f"/v1/runs/{run_id}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] in ("done", "failed", "warning", "passed", "queued", "running")
    assert body.get("progress") is not None or body["status"] == "done"


@pytest.mark.live
@pytest.mark.asyncio
async def test_run_events_sse_smoke(live_client):
    res = await live_client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
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

    async with live_client.stream("GET", f"/v1/runs/{run_id}/events", timeout=10.0) as stream:
        assert stream.status_code == 200
        first = b""
        async for part in stream.aiter_bytes():
            first += part
            if len(first) >= 64 or b"data:" in first:
                break
        assert b"data:" in first


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.asyncio
async def test_multipart_test_run_with_facture(live_client):
    if not FACTURE_PDF.is_file():
        pytest.skip("Facture.pdf fixture not found")

    suffix = uuid.uuid4().hex[:8]
    wf_id = f"wf-facture-api-{suffix}"
    doc_id = f"doc-facture-{suffix}"
    pdf = facture_bytes()

    saved = await live_client.put(
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
    started = await live_client.post(
        f"/v1/workflows/{wf_id}/runs",
        files=[
            ("payload", (None, payload.encode(), "application/json")),
            ("document_ids", (None, json.dumps([doc_id]).encode(), "application/json")),
            ("files", ("Facture.pdf", pdf, "application/pdf")),
        ],
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    from audit_workbench.integration.workflow_flow import poll_run_until_done

    result = await poll_run_until_done(live_client, run_id, max_ms=120_000)
    assert total_from_result(result) == EXPECTED_TOTAL


@pytest.mark.live
@pytest.mark.asyncio
async def test_test_run_produces_audit_detail(live_client):
    started = await live_client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
        json={
            "snapshot": {
                "documents": [],
                "rules": [],
                "workflowName": "Invoice Audit Pipeline",
            }
        },
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    from audit_workbench.integration.workflow_flow import poll_run_until_done

    result = await poll_run_until_done(live_client, run_id)
    audit_id = result["id"]

    detail = await live_client.get(f"/v1/audits/{audit_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == audit_id


@pytest.mark.live
@pytest.mark.asyncio
async def test_api_run_with_seed_key_completes(live_client):
    ok = await live_client.post(
        "/v1/workflows/wf-invoice-audit/runs",
        headers={"Authorization": f"Bearer {SEED_API_KEY}"},
    )
    assert ok.status_code == 202
    run_id = ok.json()["runId"]

    from audit_workbench.integration.workflow_flow import poll_run_until_done

    result = await poll_run_until_done(live_client, run_id)
    assert result is not None
