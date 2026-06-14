"""Full platform API journey against a running stack (not in-memory SQLite).

Run via: pnpm test:platform  (or pytest -m live with E2E_API_URL set)
"""

from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

BASE = os.environ.get("E2E_API_URL", "http://localhost:8000").rstrip("/")
WF_ID = "wf-invoice-audit"

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        yield c


def test_healthz(client: httpx.Client):
    res = client.get("/v1/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_metrics_and_rules_library(client: httpx.Client):
    metrics = client.get("/v1/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert "kpis" in body
    assert any(k["id"] == "auditsWeek" for k in body["kpis"])

    rules = client.get("/v1/rules/library")
    assert rules.status_code == 200
    assert len(rules.json()["rules"]) >= 1


def test_workflows_list_detail_and_seed_audit(client: httpx.Client):
    listed = client.get("/v1/workflows")
    assert listed.status_code == 200
    workflows = listed.json()["workflows"]
    assert any(w["id"] == WF_ID for w in workflows)

    detail = client.get(f"/v1/workflows/{WF_ID}")
    assert detail.status_code == 200
    assert detail.json()["workflow"]["id"] == WF_ID

    audits = client.get("/v1/audits")
    assert audits.status_code == 200
    assert any(a["id"] == "AUD-2023-8902" for a in audits.json()["audits"])

    report = client.get("/v1/audits/AUD-2023-8902")
    assert report.status_code == 200
    audit = report.json()
    assert audit["status"] == "failed"
    assert any(r["name"] == "Math integrity" for r in audit.get("ruleResults", []))


def test_dry_run_test_run_and_crud_deploy(client: httpx.Client):
    dry = client.post(
        f"/v1/workflows/{WF_ID}/dry-run",
        json={
            "fields": [
                {"id": "1", "name": "subtotal", "description": "", "sampleValue": "5625"},
                {"id": "2", "name": "tax", "description": "", "sampleValue": "478.13"},
                {"id": "3", "name": "total_amount", "description": "", "sampleValue": "6200"},
            ],
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
    assert dry.json()["ruleResults"][0]["status"] == "failed"

    test_run = client.post(
        f"/v1/workflows/{WF_ID}/test-run",
        json={"documents": [], "rules": [], "workflowName": "Invoice Audit Pipeline"},
    )
    assert test_run.status_code == 200
    body = test_run.json()
    assert body["status"] in ("passed", "failed", "warning")
    audit_id = body["id"]

    detail = client.get(f"/v1/audits/{audit_id}")
    assert detail.status_code == 200

    created = client.post(
        "/v1/workflows",
        json={"name": "Platform E2E WF", "description": "live", "owner": "e2e"},
    )
    assert created.status_code == 201
    wf = created.json()["workflow"]
    wf_id = wf["id"]
    suffix = uuid.uuid4().hex[:8]
    doc_id = f"doc-e2e-{suffix}"
    field_id = f"f-e2e-{suffix}"
    rule_id = f"rule-e2e-{suffix}"

    updated = client.put(
        f"/v1/workflows/{wf_id}",
        json={
            "id": wf_id,
            "name": wf["name"],
            "description": wf.get("description", ""),
            "status": wf.get("status", "draft"),
            "owner": wf.get("owner", "e2e"),
            "documents": [
                {
                    "id": doc_id,
                    "documentType": "Invoice",
                    "schema": [{"id": field_id, "name": "total_amount", "description": "Total"}],
                }
            ],
            "rules": [
                {
                    "id": rule_id,
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
    assert updated.status_code == 200

    deployed = client.post(f"/v1/workflows/{wf_id}/deploy", json={})
    assert deployed.status_code == 200
    assert deployed.json()["workflow"]["deployedAt"]


def test_api_run_poll(client: httpx.Client):
    wf = client.get(f"/v1/workflows/{WF_ID}")
    assert wf.status_code == 200
    key = wf.json()["workflow"]["apiKey"]

    unauthorized = client.post(f"/v1/workflows/{WF_ID}/run")
    assert unauthorized.status_code == 401

    started = client.post(
        f"/v1/workflows/{WF_ID}/run",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    for _ in range(40):
        poll = client.get(f"/v1/runs/{run_id}")
        assert poll.status_code == 200
        body = poll.json()
        if body["status"] in ("done", "failed"):
            if body["status"] == "failed":
                pytest.fail(body.get("error") or "run failed")
            assert body["result"] is not None
            return
        time.sleep(0.25)

    pytest.fail(f"Run {run_id} did not complete in time")
