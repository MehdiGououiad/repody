import pytest


@pytest.mark.asyncio
async def test_healthz(client):
    res = await client.get("/v1/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_platform_config(client):
    res = await client.get("/v1/platform/config")
    assert res.status_code == 200
    body = res.json()
    assert "extractor" in body
    assert "queueBackend" in body
    assert "maxUploadBytes" in body


@pytest.mark.asyncio
async def test_workflows_list_and_detail(client):
    res = await client.get("/v1/workflows")
    assert res.status_code == 200
    workflows = res.json()["workflows"]
    assert len(workflows) >= 1
    wf_id = workflows[0]["id"]
    detail = await client.get(f"/v1/workflows/{wf_id}")
    assert detail.status_code == 200
    assert detail.json()["workflow"]["id"] == wf_id


@pytest.mark.asyncio
async def test_rules_library(client):
    res = await client.get("/v1/rules/library")
    assert res.status_code == 200
    rules = res.json()["rules"]
    assert len(rules) >= 1


@pytest.mark.asyncio
async def test_metrics(client):
    res = await client.get("/v1/metrics")
    assert res.status_code == 200
    body = res.json()
    assert "kpis" in body
    assert "performanceSeries" in body


@pytest.mark.asyncio
async def test_seed_workflow_cannot_be_archived(client):
    res = await client.delete("/v1/workflows/wf-invoice-audit")
    assert res.status_code == 404
    detail = await client.get("/v1/workflows/wf-invoice-audit")
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_dry_run(client):
    res = await client.post(
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
    assert res.status_code == 200
    data = res.json()
    assert data["ruleResults"][0]["status"] == "skipped"


@pytest.mark.asyncio
async def test_test_run_and_audit_detail(client):
    res = await client.post(
        "/v1/workflows/wf-invoice-audit/test-run",
        json={"documents": [], "rules": [], "workflowName": "Invoice Audit Pipeline"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "id" in body
    assert body["status"] in ("passed", "failed", "warning")
    audit_id = body["id"]

    detail = await client.get(f"/v1/audits/{audit_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == audit_id


@pytest.mark.asyncio
async def test_workflow_crud(client):
    created = await client.post(
        "/v1/workflows",
        json={"name": "E2E Workflow", "description": "test", "owner": "Tester"},
    )
    assert created.status_code == 201
    wf = created.json()["workflow"]
    wf_id = wf["id"]

    updated = await client.put(
        f"/v1/workflows/{wf_id}",
        json={
            **wf,
            "name": "E2E Updated",
            "documents": [
                {
                    "id": "doc1",
                    "documentType": "Invoice",
                    "schema": [{"id": "f-e2e-1", "name": "total_amount", "description": "Total"}],
                }
            ],
            "rules": [
                {
                    "id": "rule1",
                    "name": "Positive total",
                    "kind": "logic",
                    "scope": "intra",
                    "appliesTo": ["doc1"],
                    "body": "total_amount > 0",
                    "severity": "reject",
                }
            ],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["workflow"]["name"] == "E2E Updated"

    deployed = await client.post(f"/v1/workflows/{wf_id}/deploy", json={})
    assert deployed.status_code == 200
    assert deployed.json()["workflow"]["deployedAt"]


@pytest.mark.asyncio
async def test_workflow_put_create_and_post_put_upsert(client):
    """PUT creates a new workflow; a second PUT updates without duplicate-key errors."""
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
async def test_api_run_requires_key(client):
    res = await client.post("/v1/workflows/wf-invoice-audit/run")
    assert res.status_code == 401

    ok = await client.post(
        "/v1/workflows/wf-invoice-audit/run",
        headers={"Authorization": f"Bearer {SEED_API_KEY}"},
    )
    assert ok.status_code == 202
    run_id = ok.json()["runId"]

    poll = await client.get(f"/v1/runs/{run_id}")
    assert poll.status_code == 200
    body = poll.json()
    assert body["status"] in ("done", "failed")
    if body["status"] == "failed":
        pytest.fail(body.get("error") or "run failed")
    assert body["result"] is not None
    assert poll.json()["result"] is not None


@pytest.mark.asyncio
async def test_audits_list(client):
    res = await client.get("/v1/audits")
    assert res.status_code == 200
    audits = res.json()["audits"]
    assert len(audits) >= 1
