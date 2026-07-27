"""Locust HTTP load profile — control-plane / readiness (not VLM extraction).

Extraction scale is measured by ``prod_stress_test.py`` (presign → Taskiq → llama-server).

Usage:
  STRESS_BEARER=... locust -f backend/scripts/locust_api_load.py --headless \\
    -u 40 -r 10 -t 90s --host http://127.0.0.1:8000 \\
    --csv benchmark-reports/locust-api --html benchmark-reports/locust-api.html
"""

from __future__ import annotations

import os

from locust import HttpUser, between, task


class ApiControlPlaneUser(HttpUser):
    wait_time = between(0.05, 0.25)

    def on_start(self) -> None:
        token = (os.environ.get("STRESS_BEARER") or "").strip()
        if token:
            self.client.headers["Authorization"] = f"Bearer {token}"

    @task(5)
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

    @task(1)
    def list_workflows(self) -> None:
        # Auth required when OIDC is on; may 429 under HTTP rate limits (expected).
        with self.client.get("/v1/workflows", name="GET /v1/workflows", catch_response=True) as res:
            if res.status_code in (200, 429):
                res.success()
            else:
                res.failure(f"status={res.status_code}")