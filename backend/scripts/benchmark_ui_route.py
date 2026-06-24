#!/usr/bin/env python3
"""Benchmark the unified UI workflow-run path (presign + POST /runs/json when available).

Runs four scenarios on two copies of Facture.pdf:
  1. VLM extraction + intra logic rules
  2. VLM + intra logic + LLM rules
  3. VLM + cross-document logic
  4. VLM + cross-document logic + LLM

Usage:
  python backend/scripts/benchmark_ui_route.py --api http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from audit_workbench.extraction.model_registry import REPODY_VLM_CATALOG_ID

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF = REPO_ROOT / "e2e" / "fixtures" / "documents" / "Facture.pdf"


@dataclass(frozen=True)
class Scenario:
    id: str
    label: str
    rules: list[dict[str, Any]]


def _fetch_oidc_token(
    *,
    keycloak: str,
    realm: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
) -> str | None:
    import urllib.error
    import urllib.parse
    import urllib.request

    token_url = f"{keycloak.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        }
    ).encode("utf-8")
    req = urllib.request.Request(token_url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode("utf-8"))
            return payload.get("access_token")
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None


def _doc_defs(doc_a: str, doc_b: str, *, probe: str | None = None) -> list[dict[str, Any]]:
    def field(name: str, description: str) -> dict[str, str]:
        return {"id": f"f-{uuid.uuid4().hex[:8]}", "name": name, "description": description}

    def schema() -> list[dict[str, str]]:
        rows = [
            field("total_amount", "Total TTC"),
            field("tva", "Total TVA"),
        ]
        if probe:
            rows.append(field(probe, "Cache-bust probe; ignore if absent."))
        return rows

    return [
        {
            "id": doc_a,
            "documentType": "Facture 1",
            "extractionMode": "document_model",
            "validationMode": "logic_only",
            "ocrModel": REPODY_VLM_CATALOG_ID,
            "schema": schema(),
        },
        {
            "id": doc_b,
            "documentType": "Facture 2",
            "extractionMode": "document_model",
            "validationMode": "logic_only",
            "ocrModel": REPODY_VLM_CATALOG_ID,
            "schema": schema(),
        },
    ]


def _scenarios(doc_a: str, doc_b: str) -> list[Scenario]:
    def rid(suffix: str) -> str:
        return f"rule-{suffix}-{uuid.uuid4().hex[:6]}"

    return [
        Scenario(
            "logic-intra",
            "Intra logic only",
            [
                {
                    "id": rid("intra-a"),
                    "name": "Facture 1 total is 6000",
                    "kind": "logic",
                    "scope": "intra",
                    "appliesTo": [doc_a],
                    "body": "total_amount == 6000",
                    "severity": "reject",
                },
                {
                    "id": rid("intra-b"),
                    "name": "Facture 2 total is 6000",
                    "kind": "logic",
                    "scope": "intra",
                    "appliesTo": [doc_b],
                    "body": "total_amount == 6000",
                    "severity": "reject",
                },
            ],
        ),
        Scenario(
            "logic-llm-intra",
            "Intra logic + LLM",
            [
                {
                    "id": rid("logic"),
                    "name": "Facture 1 total is 6000",
                    "kind": "logic",
                    "scope": "intra",
                    "appliesTo": [doc_a],
                    "body": "total_amount == 6000",
                    "severity": "reject",
                },
                {
                    "id": rid("llm"),
                    "name": "LLM confirms invoice total",
                    "kind": "llm",
                    "scope": "intra",
                    "appliesTo": [doc_a],
                    "body": "The invoice total_amount must be exactly 6000 euros. Fail if different.",
                    "severity": "reject",
                },
            ],
        ),
        Scenario(
            "logic-cross",
            "Cross-document logic",
            [
                {
                    "id": rid("cross"),
                    "name": "Totals match across invoices",
                    "kind": "logic",
                    "scope": "cross",
                    "appliesTo": [doc_a, doc_b],
                    "body": "facture_1__total_amount == facture_2__total_amount",
                    "severity": "reject",
                },
            ],
        ),
        Scenario(
            "logic-llm-cross",
            "Cross logic + LLM",
            [
                {
                    "id": rid("cross-logic"),
                    "name": "Totals match across invoices",
                    "kind": "logic",
                    "scope": "cross",
                    "appliesTo": [doc_a, doc_b],
                    "body": "facture_1__total_amount == facture_2__total_amount",
                    "severity": "reject",
                },
                {
                    "id": rid("cross-llm"),
                    "name": "LLM confirms matching totals",
                    "kind": "llm",
                    "scope": "cross",
                    "appliesTo": [doc_a, doc_b],
                    "body": (
                        "Both invoices must show the same total_amount. "
                        "Fail if Facture 1 and Facture 2 totals differ."
                    ),
                    "severity": "reject",
                },
            ],
        ),
    ]


async def _poll_run(
    client: httpx.AsyncClient,
    run_id: str,
    *,
    timeout_s: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    delay = 0.35
    while time.monotonic() < deadline:
        status_res = await client.get(f"/v1/runs/{run_id}/status")
        status_res.raise_for_status()
        body = status_res.json()
        if body.get("status") == "failed":
            raise RuntimeError(body.get("error") or "Run failed")
        if body.get("status") == "done":
            detail_res = await client.get(f"/v1/runs/{run_id}")
            detail_res.raise_for_status()
            detail = detail_res.json()
            if not detail.get("result"):
                raise RuntimeError("Run finished without result")
            return detail
        await asyncio.sleep(delay)
        delay = min(1.5, delay + 0.1)
    raise TimeoutError(f"Run {run_id} timed out after {timeout_s:.0f}s")


async def _upload_presign(
    client: httpx.AsyncClient,
    *,
    doc_id: str,
    filename: str,
    data: bytes,
    mime: str,
) -> dict[str, str]:
    presign_res = await client.post(
        "/v1/uploads/presign",
        json={
            "files": [
                {
                    "fileName": filename,
                    "mimeType": mime,
                    "size": len(data),
                    "documentId": doc_id,
                }
            ]
        },
    )
    presign_res.raise_for_status()
    payload = presign_res.json()
    if payload.get("uploadMode") != "presigned":
        raise RuntimeError("presign_unavailable")
    item = payload["uploads"][0]
    upload_url = item.get("uploadUrl")
    if not upload_url:
        raise RuntimeError("Missing presign upload URL")

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as put_client:
        put_res = await put_client.put(
            upload_url,
            content=data,
            headers=item.get("headers") or {"Content-Type": mime},
        )
        put_res.raise_for_status()

    confirm_res = await client.post(
        "/v1/uploads/confirm",
        json={"storageKeys": [item["storageKey"]]},
    )
    confirm_res.raise_for_status()
    return {
        "documentId": doc_id,
        "storageKey": item["storageKey"],
        "mimeType": mime,
        "fileName": filename,
    }


async def _run_scenario(
    client: httpx.AsyncClient,
    *,
    workflow_id: str,
    scenario: Scenario,
    documents: list[dict[str, Any]],
    pdf_bytes: bytes,
    timeout_s: float,
    route: str,
) -> dict[str, Any]:
    save_res = await client.put(
        f"/v1/workflows/{workflow_id}",
        json={
            "id": workflow_id,
            "name": f"Benchmark · {scenario.label}",
            "description": "benchmark_ui_route.py",
            "status": "draft",
            "owner": "benchmark",
            "documents": documents,
            "rules": scenario.rules,
        },
    )
    save_res.raise_for_status()

    snapshot = {
        "documents": documents,
        "rules": scenario.rules,
        "workflowName": f"Benchmark · {scenario.label}",
    }
    doc_ids = [documents[0]["id"], documents[1]["id"]]
    wall_started = time.perf_counter()

    if route == "presign":
        bindings = await asyncio.gather(
            *[
                _upload_presign(
                    client,
                    doc_id=doc_id,
                    filename="Facture.pdf",
                    data=pdf_bytes,
                    mime="application/pdf",
                )
                for doc_id in doc_ids
            ]
        )
        start_res = await client.post(
            f"/v1/workflows/{workflow_id}/runs/json",
            json={"snapshot": snapshot, "fileBindings": list(bindings)},
        )
    else:
        multipart: list[tuple[str, tuple[str | None, bytes, str]]] = [
            ("payload", (None, json.dumps(snapshot).encode(), "application/json")),
            ("document_ids", (None, json.dumps(doc_ids).encode(), "application/json")),
            ("files", ("Facture.pdf", pdf_bytes, "application/pdf")),
            ("files", ("Facture.pdf", pdf_bytes, "application/pdf")),
        ]
        start_res = await client.post(
            f"/v1/workflows/{workflow_id}/runs",
            files=multipart,
        )

    start_res.raise_for_status()
    run_id = start_res.json()["runId"]
    detail = await _poll_run(client, run_id, timeout_s=timeout_s)
    wall_ms = round((time.perf_counter() - wall_started) * 1000)

    result = detail["result"]
    metadata = result.get("metadata") or {}
    docs = result.get("documents") or []
    extraction_ms = 0
    cache_hits = 0
    per_doc_extract: list[int] = []
    for doc in docs:
        meta = doc.get("extraction") or {}
        ms = int(meta.get("extractionMs") or 0)
        per_doc_extract.append(ms)
        extraction_ms += ms
        if meta.get("cacheHit"):
            cache_hits += 1

    progress = detail.get("progress") or result.get("progress") or {}
    steps = progress.get("steps") or []
    step_timings = {
        str(step.get("id") or ""): step.get("durationMs")
        for step in steps
        if step.get("durationMs") is not None
    }

    rule_results = result.get("ruleResults") or []
    failed_rules = [
        r
        for r in rule_results
        if r.get("status") in ("failed", "error")
    ]

    return {
        "scenario": scenario.id,
        "label": scenario.label,
        "route": route,
        "runId": run_id,
        "wallMs": wall_ms,
        "durationMs": metadata.get("durationMs"),
        "queueMs": None,
        "extractionMs": metadata.get("extractionMs") or extraction_ms,
        "perDocExtractionMs": per_doc_extract,
        "validationMs": metadata.get("validationMs"),
        "validationMode": metadata.get("validationMode"),
        "cacheHits": cache_hits,
        "docCount": len(docs),
        "fieldsExtracted": metadata.get("fieldsExtracted"),
        "overallStatus": result.get("status"),
        "failedRules": [
            {"name": r.get("name"), "status": r.get("status"), "detail": r.get("detail")}
            for r in failed_rules
        ],
        "stepTimings": step_timings,
        "error": None if not failed_rules else f"{len(failed_rules)} rule(s) not passed",
    }


def _print_table(rows: list[dict[str, Any]]) -> None:
    headers = (
        "scenario",
        "route",
        "wall",
        "extract",
        "validate",
        "cache",
        "status",
        "per-doc-extract",
    )
    print("\n" + " | ".join(f"{h:>14}" for h in headers))
    print("-" * 130)
    for row in rows:
        per_doc = row.get("perDocExtractionMs") or []
        print(
            " | ".join(
                f"{str(v):>14}"
                for v in (
                    row.get("scenario"),
                    row.get("route"),
                    row.get("wallMs"),
                    row.get("extractionMs"),
                    row.get("validationMs"),
                    row.get("cacheHits"),
                    row.get("overallStatus"),
                    "+".join(str(x) for x in per_doc) if per_doc else "-",
                )
            )
        )


async def run(args: argparse.Namespace) -> int:
    pdf_path = args.document
    if not pdf_path.is_file():
        print(f"Missing document: {pdf_path}", file=sys.stderr)
        return 2

    pdf_bytes = pdf_path.read_bytes()
    headers: dict[str, str] = {}
    token = _fetch_oidc_token(
        keycloak=args.keycloak,
        realm=args.realm,
        client_id=args.client_id,
        client_secret=args.client_secret,
        username=args.username,
        password=args.password,
    )
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = httpx.Timeout(connect=15.0, read=args.timeout_seconds + 60, write=120.0, pool=10.0)
    rows: list[dict[str, Any]] = []
    environment: dict[str, Any] = {}

    async with httpx.AsyncClient(
        base_url=args.api.rstrip("/"),
        headers=headers,
        timeout=timeout,
    ) as client:
        try:
            health = (await client.get("/v1/healthz")).json()
            environment["health"] = health
            try:
                environment["platform"] = (await client.get("/v1/platform/config")).json()
            except httpx.HTTPError:
                environment["platform"] = {}
            try:
                environment["uploadCapabilities"] = (
                    await client.get("/v1/uploads/capabilities")
                ).json()
            except httpx.HTTPError:
                environment["uploadCapabilities"] = {}
            try:
                environment["diagnostics"] = (await client.get("/v1/diagnostics")).json()
            except httpx.HTTPError:
                environment["diagnostics"] = {}
        except httpx.HTTPError as exc:
            print(f"Cannot reach API at {args.api}: {exc}", file=sys.stderr)
            return 2

        caps = environment.get("uploadCapabilities") or {}
        default_route = (
            "presign"
            if caps.get("directUploadEnabled") and caps.get("uploadMode") == "presigned"
            else "multipart"
        )
        route = args.route or default_route
        print(f"API: {args.api}  route: {route}  cold: {args.cold}  auth: {'yes' if token else 'no'}")
        print(
            f"LLM validation: {environment.get('diagnostics', {}).get('llmValidationEnabled')}  "
            f"parallel extraction: {environment.get('platform', {}).get('parallelDocExtraction', 'unknown')}"
        )

        suite_id = uuid.uuid4().hex[:8]

        for scenario_id, scenario_label in (
            ("logic-intra", "Intra logic only"),
            ("logic-llm-intra", "Intra logic + LLM"),
            ("logic-cross", "Cross-document logic"),
            ("logic-llm-cross", "Cross logic + LLM"),
        ):
            doc_a = f"doc-a-{uuid.uuid4().hex[:6]}"
            doc_b = f"doc-b-{uuid.uuid4().hex[:6]}"
            scenario_docs = _doc_defs(
                doc_a,
                doc_b,
                probe=f"_bench_probe_{suite_id}_{scenario_id}" if args.cold else None,
            )
            rules = [s for s in _scenarios(doc_a, doc_b) if s.id == scenario_id][0].rules
            workflow_id = f"wf-bench-{suite_id}-{scenario_id}"
            print(f"\n[{scenario_id}] {scenario_label} …", flush=True)
            try:
                row = await _run_scenario(
                    client,
                    workflow_id=workflow_id,
                    scenario=Scenario(scenario_id, scenario_label, rules),
                    documents=scenario_docs,
                    pdf_bytes=pdf_bytes,
                    timeout_s=args.timeout_seconds,
                    route=route,
                )
            except Exception as exc:
                row = {
                    "scenario": scenario_id,
                    "label": scenario_label,
                    "route": route,
                    "error": str(exc),
                    "wallMs": None,
                }
            rows.append(row)
            print(
                f"  wall={row.get('wallMs')}ms extract={row.get('extractionMs')}ms "
                f"validate={row.get('validationMs')}ms status={row.get('overallStatus')} "
                f"cache={row.get('cacheHits')}",
                flush=True,
            )
            if row.get("error"):
                print(f"  error: {row['error']}", flush=True)
            try:
                await client.delete(f"/v1/workflows/{workflow_id}")
            except httpx.HTTPError:
                pass

    _print_table(rows)
    wall_times = [int(r["wallMs"]) for r in rows if isinstance(r.get("wallMs"), int)]
    extract_times = [int(r["extractionMs"]) for r in rows if isinstance(r.get("extractionMs"), int)]
    validate_times = [int(r["validationMs"]) for r in rows if isinstance(r.get("validationMs"), int)]

    print("\n--- Bottleneck summary ---")
    if wall_times:
        print(f"Median wall time: {statistics.median(wall_times):.0f} ms")
    if extract_times:
        print(
            f"Median extraction: {statistics.median(extract_times):.0f} ms "
            f"({100 * statistics.median(extract_times) / statistics.median(wall_times):.0f}% of wall)"
            if wall_times
            else f"Median extraction: {statistics.median(extract_times):.0f} ms"
        )
    if validate_times:
        print(
            f"Median validation: {statistics.median(validate_times):.0f} ms "
            f"({100 * statistics.median(validate_times) / statistics.median(wall_times):.0f}% of wall)"
            if wall_times
            else f"Median validation: {statistics.median(validate_times):.0f} ms"
        )

    report = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "api": args.api,
        "route": route,
        "document": str(pdf_path),
        "documentBytes": len(pdf_bytes),
        "environment": environment,
        "results": rows,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport: {args.output}")

    failed = sum(1 for r in rows if r.get("error") or r.get("overallStatus") == "failed")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--document", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--route", choices=("presign", "multipart"), default=None)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument(
        "--cold",
        action="store_true",
        help="Bust extraction cache with a unique probe field per scenario",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--keycloak", default="http://127.0.0.1:8080")
    parser.add_argument("--realm", default="repody")
    parser.add_argument("--client-id", default="repody-web")
    parser.add_argument("--client-secret", default="repody-web-dev-secret")
    parser.add_argument("--username", default="operator@repody.local")
    parser.add_argument("--password", default="repody-dev")
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
