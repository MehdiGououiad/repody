"""A running stack with workers and the llama-server: run the demo workflow on Facture.pdf.

E2E_API_URL=http://127.0.0.1:8000 uv run pytest -m live
"""

from __future__ import annotations

import os
import time

import httpx
import pytest
from tests.conftest import FACTURE_PDF

from repody.app.seed import SEED_API_KEY
from repody.rules.values import parse_numeric_value

API = os.environ.get("E2E_API_URL", "http://127.0.0.1:8000")
AUTH = {"Authorization": f"Bearer {SEED_API_KEY}"}


@pytest.fixture(scope="module")
def http():
    with httpx.Client(base_url=API, timeout=30) as client:
        if client.get("/v1/healthz").status_code != 200:
            pytest.skip(f"no healthy stack at {API}")
        yield client


def test_demo_workflow_on_facture(http: httpx.Client):
    started = http.post(
        "/v1/workflows/wf-invoice-audit/runs",
        files={"files": ("Facture.pdf", FACTURE_PDF.read_bytes(), "application/pdf")},
        data={"documents": "Invoice"},
        headers=AUTH,
    )
    assert started.status_code == 202, started.text
    run_id = started.json()["runId"]

    deadline = time.monotonic() + 300
    while (state := http.get(f"/v1/runs/{run_id}", headers=AUTH).json())["status"] in (
        "queued",
        "running",
    ):
        assert time.monotonic() < deadline, state
        time.sleep(1)

    assert state["status"] == "done", state
    report = state["result"]
    fields = {f["key"]: f["value"] for f in report["documents"][0]["fields"]}
    print(fields, [(r["name"], r["status"], r["detail"]) for r in report["ruleResults"]])
    assert parse_numeric_value(fields["total_amount"]) == 6000.0
    assert parse_numeric_value(fields["tax"]) == 1000.0
    assert report["ruleResults"][0]["status"] == "passed"  # 5000 + 1000 == 6000
