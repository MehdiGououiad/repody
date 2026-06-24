#!/usr/bin/env python3
"""Custom-document benchmark: cold, warm, and cache-hit phases for VLM + Surya."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

from tests.helpers.live_stack import fetch_keycloak_token

API = "http://api.repody.local"
PDF = Path(__file__).resolve().parents[2] / "e2e/fixtures/documents/Facture.pdf"


def main() -> int:
    headers = {"Authorization": f"Bearer {fetch_keycloak_token()}"}
    pdf = PDF.read_bytes()
    data = {
        "profile": "models",
        "models": json.dumps(["repody:vlm", "surya-ocr2"]),
        "validation_mode": "logic_only",
        "warm_runs": "1",
        "minimum_accuracy": "0",
        "cache_check": "true",
        "judge_quality": "true",
    }
    files = {"document": ("custom-facture.pdf", pdf, "application/pdf")}

    with httpx.Client(headers=headers, timeout=30.0) as client:
        start = client.post(f"{API}/v1/operator/benchmarks", data=data, files=files, timeout=120.0)
        start.raise_for_status()
        job_id = start.json()["job"]["id"]
        print("job", job_id)

        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            job = client.get(f"{API}/v1/operator/jobs/{job_id}").json()
            print("status", job["status"])
            if job["status"] in {"completed", "failed"}:
                break
            time.sleep(5)
        else:
            print("timeout")
            return 1

        if job["status"] != "completed":
            print((job.get("output") or "")[-2000:])
            return 1

        report = client.get(f"{API}/v1/operator/jobs/{job_id}/report", timeout=60.0).json()
        rows = report.get("results", [])
        for row in rows:
            print(
                row["case"],
                row["phase"],
                row["status"],
                f"cache={row.get('cacheHit')}",
                f"ocr={row.get('ocrTextChars')}",
                f"raw={row.get('rawTextChars')}",
                f"preview={len(row.get('textPreview') or '')}",
                row.get("error"),
            )

        by_case: dict[str, list[dict]] = {}
        for row in rows:
            by_case.setdefault(row["case"], []).append(row)

        failures: list[str] = []
        for case, case_rows in by_case.items():
            phases = {r["phase"]: r for r in case_rows}
            first = phases.get("first")
            warm = phases.get("warm-1")
            cache = phases.get("cache")
            if not first or not first.get("passed"):
                failures.append(f"{case}: first phase failed")
            if not warm or not warm.get("passed"):
                failures.append(f"{case}: warm-1 failed")
            if not cache or not cache.get("passed"):
                failures.append(f"{case}: cache phase failed")
            elif cache.get("cacheHit") is not True:
                failures.append(f"{case}: cache phase expected cacheHit=true")
            preview_len = len((first or {}).get("textPreview") or "")
            if preview_len < 20:
                failures.append(f"{case}: markdown preview too short ({preview_len})")

        if failures:
            print("FAILURES:")
            for item in failures:
                print(" -", item)
            return 1

        print("CACHE E2E OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
