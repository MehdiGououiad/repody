#!/usr/bin/env python3
"""Live smoke: custom-document benchmark with markdown preview and optional cache."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

from tests.helpers.live_stack import fetch_keycloak_token

API = "http://api.repody.local"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {fetch_keycloak_token()}"}


def start_benchmark(
    client: httpx.Client,
    *,
    pdf: bytes,
    warm_runs: int,
    cache_check: bool,
    models: list[str],
) -> str:
    data = {
        "profile": "models",
        "models": json.dumps(models),
        "validation_mode": "logic_only",
        "warm_runs": str(warm_runs),
        "minimum_accuracy": "0",
        "cache_check": str(cache_check).lower(),
        "judge_quality": "true",
    }
    files = {"document": ("custom-facture.pdf", pdf, "application/pdf")}
    response = client.post(
        f"{API}/v1/operator/benchmarks",
        data=data,
        files=files,
        timeout=120.0,
    )
    print("start", response.status_code, response.text[:400])
    response.raise_for_status()
    return response.json()["job"]["id"]


def wait_job(client: httpx.Client, job_id: str, *, timeout_s: int = 600) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        job = client.get(f"{API}/v1/operator/jobs/{job_id}", timeout=30.0).json()
        status = job["status"]
        print("job", job_id, status)
        if status in {"completed", "failed"}:
            return job
        time.sleep(5)
    raise TimeoutError(f"job {job_id} did not finish in {timeout_s}s")


def print_report(client: httpx.Client, job_id: str) -> dict:
    response = client.get(f"{API}/v1/operator/jobs/{job_id}/report", timeout=60.0)
    print("report", response.status_code)
    response.raise_for_status()
    report = response.json()
    for row in report.get("results", []):
        preview = row.get("textPreview") or ""
        print(
            row.get("case"),
            row.get("phase"),
            row.get("status"),
            f"ocrChars={row.get('ocrTextChars')}",
            f"cacheHit={row.get('cacheHit')}",
            f"previewLen={len(preview)}",
            f"error={row.get('error')}",
        )
        if preview:
            print("previewHead:", preview[:200].replace("\n", " "))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warm-runs", type=int, default=0)
    parser.add_argument("--cache-check", action="store_true")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "e2e/fixtures/documents/Facture.pdf",
    )
    parser.add_argument("--models", default='["repody:vlm"]')
    args = parser.parse_args()
    pdf = args.pdf.read_bytes()
    models = json.loads(args.models)

    with httpx.Client(headers=_headers(), timeout=30.0) as client:
        job_id = start_benchmark(
            client,
            pdf=pdf,
            warm_runs=args.warm_runs,
            cache_check=args.cache_check,
            models=models,
        )
        job = wait_job(client, job_id)
        if job["status"] != "completed":
            print("JOB FAILED", job.get("error") or job.get("output"))
            return 1
        report = print_report(client, job_id)

    failed = [r for r in report.get("results", []) if not r.get("passed") and not r.get("skipped")]
    empty_preview = [
        r
        for r in report.get("results", [])
        if r.get("judgeQuality") and not (r.get("textPreview") or "").strip()
    ]
    if failed:
        print("FAILED ROWS", len(failed))
        return 1
    if empty_preview:
        print("EMPTY PREVIEW ROWS", len(empty_preview))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
