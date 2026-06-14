#!/usr/bin/env python3
"""
Platform integration suite for fresh-environment deployment verification.

Usage:
  python backend/scripts/platform_integration_suite.py
  python backend/scripts/platform_integration_suite.py --api http://localhost:8000 --skip-extraction
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(ROOT / "backend"))

from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID  # noqa: E402
from tests.test_e2e.facture_helpers import (  # noqa: E402
    EXPECTED_TOTAL,
    EXPECTED_TVA,
    FACTURE_PDF,
    LOGIC_RULE_TOTAL_OK,
    LOGIC_RULE_TVA_UNDER_500,
    WORKFLOW_NAME,
    document_def,
    document_def_tva,
    facture_bytes,
    rule_status_from_result,
    total_from_result,
    tva_from_result,
)
from tests.test_e2e.ui_flow import poll_run_until_done, save_workflow  # noqa: E402

DEFAULT_DOCUMENT_MODEL = REPODY_VLM_CATALOG_ID
MAX_WAIT_MS = 900_000


def _auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _resolve_admin_token(cli_token: str | None) -> str | None:
    if cli_token:
        return cli_token.strip() or None
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("AUDIT_ADMIN_API_TOKEN="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value
    env = os.environ.get("AUDIT_ADMIN_API_TOKEN")
    return env.strip() if env else None


@dataclass
class StepResult:
    name: str
    passed: bool
    detail: str = ""
    duration_s: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationReport:
    api: str
    steps: list[StepResult] = field(default_factory=list)

    def add(self, step: StepResult) -> None:
        self.steps.append(step)
        icon = "PASS" if step.passed else "FAIL"
        print(f"[{icon}] {step.name} ({step.duration_s:.2f}s)")
        if step.detail:
            print(f"       {step.detail}")

    @property
    def ok(self) -> bool:
        return all(step.passed for step in self.steps)


async def _timed(name: str, report: IntegrationReport, coro) -> Any:
    t0 = time.perf_counter()
    try:
        result = await coro
        report.add(StepResult(name=name, passed=True, duration_s=time.perf_counter() - t0, data=result if isinstance(result, dict) else {}))
        return result
    except Exception as exc:
        report.add(StepResult(name=name, passed=False, detail=str(exc), duration_s=time.perf_counter() - t0))
        return None


async def presign_upload(client: httpx.AsyncClient, doc_id: str, pdf: bytes) -> dict:
    presign = await client.post(
        "/v1/uploads/presign",
        json={
            "files": [
                {
                    "fileName": "Facture.pdf",
                    "mimeType": "application/pdf",
                    "size": len(pdf),
                    "documentId": doc_id,
                }
            ]
        },
    )
    presign.raise_for_status()
    item = presign.json()["uploads"][0]
    async with httpx.AsyncClient(timeout=120.0) as raw:
        put = await raw.put(
            item["uploadUrl"],
            content=pdf,
            headers=item.get("headers") or {"Content-Type": "application/pdf"},
        )
        put.raise_for_status()
    confirm = await client.post(
        "/v1/uploads/confirm",
        json={"storageKeys": [item["storageKey"]]},
    )
    confirm.raise_for_status()
    return confirm.json()["uploads"][0]


async def run_extraction_case(
    client: httpx.AsyncClient,
    *,
    wf_id: str,
    doc_id: str,
    pdf: bytes,
    documents: list[dict],
    rules: list[dict],
    expect_status: str,
    assert_total: str | None = None,
    assert_tva: str | None = None,
    assert_rule: tuple[str, str] | None = None,
) -> dict:
    await save_workflow(client, wf_id=wf_id, name=WORKFLOW_NAME, documents=documents, rules=rules)
    binding = await presign_upload(client, doc_id, pdf)
    start = await client.post(
        f"/v1/workflows/{wf_id}/runs/json?mode=test",
        json={
            "payload": {"documents": documents, "rules": rules, "workflowName": WORKFLOW_NAME},
            "fileBindings": [
                {
                    "documentId": doc_id,
                    "storageKey": binding["storageKey"],
                    "mimeType": binding["mimeType"],
                    "fileName": binding["fileName"],
                }
            ],
        },
    )
    start.raise_for_status()
    run_id = start.json()["runId"]
    result = await poll_run_until_done(client, run_id, max_ms=MAX_WAIT_MS)
    if expect_status and result.get("status") != expect_status:
        raise AssertionError(f"status={result.get('status')} expected {expect_status}")
    if assert_total and total_from_result(result) != assert_total:
        raise AssertionError(f"total={total_from_result(result)!r} expected {assert_total}")
    if assert_tva and tva_from_result(result) != assert_tva:
        raise AssertionError(f"tva={tva_from_result(result)!r} expected {assert_tva}")
    if assert_rule:
        name, status = assert_rule
        got = rule_status_from_result(result, rule_name=name)
        if got != status:
            raise AssertionError(f"rule {name!r} status={got!r} expected {status}")
    return {"runId": run_id, "result": result}


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument(
        "--token",
        default=os.environ.get("AUDIT_ADMIN_API_TOKEN"),
        help="Admin API token (default: AUDIT_ADMIN_API_TOKEN env)",
    )
    parser.add_argument("--skip-extraction", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    base = args.api.rstrip("/")
    headers = _auth_headers(_resolve_admin_token(args.token))

    if not FACTURE_PDF.is_file():
        print(f"Missing fixture: {FACTURE_PDF}", file=sys.stderr)
        return 1

    pdf = facture_bytes()
    report = IntegrationReport(api=base)
    print("=" * 70)
    print("Platform integration suite")
    print(f"API: {base}")
    print(f"Auth: {'yes' if headers else 'no'}")
    print("=" * 70)

    timeout = httpx.Timeout(1200.0, connect=30.0)
    async with httpx.AsyncClient(base_url=base, timeout=timeout, headers=headers) as client:
        health = await _timed(
            "Health check",
            report,
            _check_health(client),
        )
        await _timed("Platform config", report, _check_platform_config(client))
        await _timed("Processing paths catalog", report, _check_processing_paths(client))
        await _timed("Document model catalog", report, _check_ocr_models(client))
        await _timed("Upload capabilities", report, _check_upload_capabilities(client))
        await _timed("Diagnostics (registry)", report, _check_diagnostics(client))

        if not args.skip_extraction and health:
            from tests.test_e2e.facture_helpers import FACTURE_UI_PATHS

            case = FACTURE_UI_PATHS[0]
            doc_id = f"doc-{uuid.uuid4().hex[:8]}"
            wf_id = f"wf-int-{uuid.uuid4().hex[:6]}"
            documents = [
                {
                    **document_def(case, doc_id=doc_id),
                    "schema": [
                        {"id": f"f-total-{uuid.uuid4().hex[:6]}", "name": "total_amount", "description": "Total TTC"},
                        {"id": f"f-tva-{uuid.uuid4().hex[:6]}", "name": "tva", "description": "Total TVA"},
                    ],
                }
            ]
            rules = [{**LOGIC_RULE_TOTAL_OK, "id": f"logic-{uuid.uuid4().hex[:6]}", "appliesTo": [doc_id]}]
            cold = await _timed(
                "Repody VLM extraction (cold)",
                report,
                run_extraction_case(
                    client,
                    wf_id=wf_id,
                    doc_id=doc_id,
                    pdf=pdf,
                    documents=documents,
                    rules=rules,
                    expect_status="passed",
                    assert_total=EXPECTED_TOTAL,
                    assert_rule=(LOGIC_RULE_TOTAL_OK["name"], "passed"),
                ),
            )
            if cold:
                tva = tva_from_result(cold["result"])
                if tva != EXPECTED_TVA:
                    report.add(StepResult("TVA field value", False, f"got {tva!r}, expected {EXPECTED_TVA}"))

            doc_fail = f"doc-{uuid.uuid4().hex[:8]}"
            wf_fail = f"wf-int-fail-{uuid.uuid4().hex[:6]}"
            fail_case = FACTURE_UI_PATHS[0]
            fail_docs = [
                {
                    **document_def_tva(fail_case, doc_id=doc_fail),
                    "schema": [
                        {
                            "id": f"f-tva-{uuid.uuid4().hex[:6]}",
                            "name": "tva",
                            "description": "Total TVA",
                        }
                    ],
                }
            ]
            fail_rules = [
                {
                    **LOGIC_RULE_TVA_UNDER_500,
                    "id": f"logic-{uuid.uuid4().hex[:6]}",
                    "appliesTo": [doc_fail],
                }
            ]
            await _timed(
                "Logic validation failure path",
                report,
                run_extraction_case(
                    client,
                    wf_id=wf_fail,
                    doc_id=doc_fail,
                    pdf=pdf,
                    documents=fail_docs,
                    rules=fail_rules,
                    expect_status="failed",
                    assert_tva=EXPECTED_TVA,
                    assert_rule=(LOGIC_RULE_TVA_UNDER_500["name"], "failed"),
                ),
            )

    payload = {
        "api": report.api,
        "passed": sum(1 for s in report.steps if s.passed),
        "failed": sum(1 for s in report.steps if not s.passed),
        "ok": report.ok,
        "steps": [
            {
                "name": s.name,
                "passed": s.passed,
                "detail": s.detail,
                "durationS": round(s.duration_s, 3),
                "data": s.data,
            }
            for s in report.steps
        ],
    }
    if args.output:
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("\n" + json.dumps(payload, indent=2))
    return 0 if report.ok else 1


async def _check_health(client: httpx.AsyncClient) -> dict:
    res = await client.get("/v1/healthz")
    res.raise_for_status()
    body = res.json()
    if body.get("status") != "ok":
        raise AssertionError(body)
    probe = body.get("modelRunner")
    # When AUDIT_HEALTHZ_PROBE_INFERENCE=false, modelRunner is omitted (no GPU ping).
    if probe is not None and probe is not True:
        raise AssertionError("Inference backend not reachable")
    return body


async def _check_platform_config(client: httpx.AsyncClient) -> dict:
    res = await client.get("/v1/platform/config")
    res.raise_for_status()
    body = res.json()
    if not body.get("documentModels"):
        raise AssertionError("No document models registered")
    return body


async def _check_processing_paths(client: httpx.AsyncClient) -> dict:
    res = await client.get("/v1/processing-paths")
    res.raise_for_status()
    body = res.json()
    path_ids = {p["id"] for p in body.get("paths") or []}
    if "document_model" not in path_ids:
        raise AssertionError(f"Missing document_model path: {path_ids}")
    return body


async def _check_ocr_models(client: httpx.AsyncClient) -> dict:
    res = await client.get("/v1/ocr/models")
    res.raise_for_status()
    body = res.json()
    models = body.get("models") or []
    if not any(m.get("id") == DEFAULT_DOCUMENT_MODEL for m in models):
        raise AssertionError(f"{DEFAULT_DOCUMENT_MODEL} not in catalog")
    if not any(m.get("available") for m in models):
        raise AssertionError("No document models available")
    return body


async def _check_upload_capabilities(client: httpx.AsyncClient) -> dict:
    res = await client.get("/v1/uploads/capabilities")
    res.raise_for_status()
    return res.json()


async def _check_diagnostics(client: httpx.AsyncClient) -> dict:
    res = await client.get("/v1/diagnostics/ocr")
    res.raise_for_status()
    body = res.json()
    if not body.get("ok"):
        raise AssertionError(body.get("detail") or "diagnostics failed")
    return body


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
