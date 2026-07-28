"""Locust real-world mix — control plane + JSON enqueue + poll (not VLM).

Usage:
  # PowerShell
  $env:STRESS_BEARER = (token from Keycloak)
  $env:STRESS_WORKFLOW_ID = "wf-invoice-audit"   # optional
  locust -f backend/scripts/locust_api_load.py --headless `
    -u 40 -r 10 -t 120s --host http://127.0.0.1:8000 `
    --csv benchmark-reports/locust-api --html benchmark-reports/locust-api.html
"""

from __future__ import annotations

import os
import random

from locust import HttpUser, between, task


class PlatformMixUser(HttpUser):
    """Mimics UI + API clients: browse, enqueue JSON runs, poll status."""

    wait_time = between(0.02, 0.15)

    def on_start(self) -> None:
        token = (os.environ.get("STRESS_BEARER") or "").strip()
        if token:
            self.client.headers["Authorization"] = f"Bearer {token}"
        self.workflow_id = (os.environ.get("STRESS_WORKFLOW_ID") or "").strip()
        self.active_runs: list[str] = []
        if not self.workflow_id:
            with self.client.get("/v1/workflows", name="GET /v1/workflows", catch_response=True) as res:
                if res.status_code == 200:
                    workflows = res.json().get("workflows") or []
                    if workflows:
                        self.workflow_id = workflows[0]["id"]
                        res.success()
                    else:
                        res.failure("no workflows")
                elif res.status_code in (401, 403, 429):
                    res.success()
                else:
                    res.failure(f"status={res.status_code}")

    @task(8)
    def healthz(self) -> None:
        with self.client.get("/v1/healthz", name="GET /v1/healthz", catch_response=True) as res:
            if res.status_code != 200:
                res.failure(f"status={res.status_code}")
                return
            body = res.json()
            if body.get("status") not in ("ok", "degraded"):
                res.failure(f"status={body.get('status')}")
            else:
                res.success()

    @task(3)
    def list_workflows(self) -> None:
        with self.client.get("/v1/workflows", name="GET /v1/workflows", catch_response=True) as res:
            if res.status_code in (200, 429):
                res.success()
            else:
                res.failure(f"status={res.status_code}")

    @task(2)
    def list_audits(self) -> None:
        with self.client.get("/v1/audits", name="GET /v1/audits", catch_response=True) as res:
            if res.status_code in (200, 429):
                res.success()
            else:
                res.failure(f"status={res.status_code}")

    @task(5)
    def enqueue_json(self) -> None:
        if not self.workflow_id:
            return
        with self.client.post(
            f"/v1/workflows/{self.workflow_id}/runs/json",
            json={
                "snapshot": {
                    "documents": [],
                    "rules": [],
                    "workflowName": "locust-mix",
                }
            },
            name="POST /workflows/{id}/runs/json",
            catch_response=True,
        ) as res:
            # 202 accepted; 429 rate limit; 503 admission — all expected under load.
            if res.status_code in (202, 429, 503):
                if res.status_code == 202:
                    run_id = res.json().get("runId")
                    if run_id:
                        self.active_runs.append(run_id)
                        if len(self.active_runs) > 50:
                            self.active_runs = self.active_runs[-50:]
                res.success()
            else:
                res.failure(f"status={res.status_code}")

    @task(6)
    def poll_run(self) -> None:
        if not self.active_runs:
            return
        run_id = random.choice(self.active_runs)
        with self.client.get(
            f"/v1/runs/{run_id}/status",
            name="GET /runs/{id}/status",
            catch_response=True,
        ) as res:
            if res.status_code in (200, 404, 429):
                res.success()
            else:
                res.failure(f"status={res.status_code}")
