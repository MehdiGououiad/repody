#!/usr/bin/env python3
"""
Live Hatchet E2E — Facture.pdf via document model extraction.

Requires the Docker stack and Docker Model Runner.

Usage:
  python backend/scripts/facture_hatchet_e2e.py
  python backend/scripts/facture_hatchet_e2e.py --api http://localhost:8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(ROOT / "backend"))

from audit_workbench.extraction.model_registry import REPODY_VLM_CATALOG_ID  # noqa: E402
from tests.test_e2e.facture_helpers import FACTURE_PDF, facture_bytes  # noqa: E402
from tests.test_e2e.ui_flow import poll_run_until_done, save_workflow  # noqa: E402

EXPECTED_TOTAL = 6000.0
TOTAL_FIELD = "montant_total"
WORKFLOW_NAME = "Facture Hatchet E2E"


def _doc_def(doc_id: str, field_id: str, *, ocr_model: str = REPODY_VLM_CATALOG_ID) -> dict:
    return {
        "id": doc_id,
        "documentType": "Facture",
        "extractionMode": "document_model",
        "validationMode": "logic_only",
        "ocrModel": ocr_model,
        "schema": [
            {
                "id": field_id,
                "name": TOTAL_FIELD,
                "description": "Montant total TTC (Total TTC)",
            }
        ],
    }


def _rules(rule_id: str) -> list[dict]:
    return [
        {
            "id": rule_id,
            "name": "Montant total under 2000",
            "kind": "logic",
            "scope": "intra",
            "body": f"{TOTAL_FIELD} < 2000",
            "severity": "reject",
        }
    ]


def _total_from_result(result: dict) -> float | None:
    for doc in result.get("documents") or []:
        for fld in doc.get("fields") or []:
            key = (fld.get("key") or fld.get("name") or "").strip().lower()
            if key in (TOTAL_FIELD, "total_amount", "montant_total"):
                raw = fld.get("value")
                if raw is None:
                    return None
                cleaned = str(raw).replace(" ", "").replace(",", ".")
                for token in cleaned.split():
                    try:
                        return float(token)
                    except ValueError:
                        continue
                try:
                    return float(cleaned)
                except ValueError:
                    return None
    return None


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--model", default=REPODY_VLM_CATALOG_ID)
    parser.add_argument("--max-wait-ms", type=float, default=900_000)
    args = parser.parse_args()

    if not FACTURE_PDF.is_file():
        print(f"Missing fixture: {FACTURE_PDF}", file=sys.stderr)
        return 1

    base = args.api.rstrip("/")
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    field_id = f"f-{uuid.uuid4().hex[:8]}"
    rule_id = f"rule-{uuid.uuid4().hex[:6]}"
    wf_id = f"wf-hatchet-{uuid.uuid4().hex[:6]}"
    pdf = facture_bytes()
    documents = [_doc_def(doc_id, field_id, ocr_model=args.model)]
    rules = _rules(rule_id)

    timeout = httpx.Timeout(args.max_wait_ms / 1000 + 60, connect=30.0)
    async with httpx.AsyncClient(base_url=base, timeout=timeout) as client:
        health = await client.get("/v1/healthz")
        health.raise_for_status()
        if not health.json().get("modelRunner"):
            print("Docker Model Runner is not reachable", file=sys.stderr)
            return 1

        await save_workflow(client, wf_id=wf_id, name=WORKFLOW_NAME, documents=documents, rules=rules)
        payload = json.dumps({"documents": documents, "rules": rules, "workflowName": WORKFLOW_NAME})
        started = await client.post(
            f"/v1/workflows/{wf_id}/runs?mode=test",
            files=[
                ("payload", (None, payload.encode(), "application/json")),
                ("document_ids", (None, json.dumps([doc_id]).encode(), "application/json")),
                ("files", ("Facture.pdf", pdf, "application/pdf")),
            ],
        )
        started.raise_for_status()
        run_id = started.json()["runId"]
        print(f"Run started: {run_id}")
        t0 = time.perf_counter()
        result = await poll_run_until_done(client, run_id, max_ms=args.max_wait_ms)
        elapsed = time.perf_counter() - t0

    total = _total_from_result(result)
    print(f"Total extracted : {total!r} (expected ~{EXPECTED_TOTAL})")
    print(f"Run status      : {result.get('status')}")
    print(f"Elapsed         : {elapsed:.1f}s")

    if total is None:
        print("FAIL: total field missing", file=sys.stderr)
        return 1
    if abs(total - EXPECTED_TOTAL) > 1.0:
        print(f"FAIL: unexpected total {total}", file=sys.stderr)
        return 1
    if result.get("status") != "failed":
        print("FAIL: expected validation failure (total < 2000 rule)", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
