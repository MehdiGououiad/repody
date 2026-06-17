"""Extraction experiments — use via benchmark_dev.py experiments."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_BACKEND / "src", _BACKEND):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)

import httpx

from audit_workbench.extraction.model_registry import REPODY_VLM_CATALOG_ID
from scripts.benchmark_ui_route import (
    DEFAULT_PDF,
    _fetch_oidc_token,
    _poll_run,
    _upload_presign,
)

REPO_ROOT = _REPO_ROOT


def _doc_defs(doc_ids: list[str]) -> list[dict[str, Any]]:
    def field(name: str, description: str) -> dict[str, str]:
        return {"id": f"f-{uuid.uuid4().hex[:8]}", "name": name, "description": description}

    types = ["Facture 1", "Facture 2"] if len(doc_ids) > 1 else ["Invoice"]
    docs: list[dict[str, Any]] = []
    for index, doc_id in enumerate(doc_ids):
        probe = f"probe_{doc_id}_{uuid.uuid4().hex[:8]}"
        schema = [
            field("total_amount", "Total TTC"),
            field("tva", "Total TVA"),
            field(probe, "Cache-bust probe; ignore if absent."),
        ]
        docs.append(
            {
                "id": doc_id,
                "documentType": types[min(index, len(types) - 1)],
                "extractionMode": "document_model",
                "validationMode": "logic_only",
                "ocrModel": REPODY_VLM_CATALOG_ID,
                "schema": schema,
            }
        )
    return docs


def _rules(doc_ids: list[str]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for doc_id in doc_ids:
        rules.append(
            {
                "id": f"rule-{uuid.uuid4().hex[:6]}",
                "name": f"Total is 6000 ({doc_id})",
                "kind": "logic",
                "scope": "intra",
                "appliesTo": [doc_id],
                "body": "total_amount == 6000",
                "severity": "reject",
            }
        )
    return rules


def _worker_vlm_timings(run_id: str) -> list[dict[str, Any]]:
    """Parse repody_vlm_done lines for a run from docker logs."""
    rows: list[dict[str, Any]] = []
    for container in ("repody-worker-1", "repody-worker-fast-1"):
        try:
            proc = subprocess.run(
                ["docker", "logs", "--tail", "500", container],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        lines = (proc.stdout or "") + (proc.stderr or "")
        for line in lines.splitlines():
            if run_id not in line or "repody_vlm_done" not in line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(
                {
                    "elapsedMs": payload.get("elapsed_ms"),
                    "promptMs": payload.get("prompt_ms"),
                    "predictedMs": payload.get("predicted_ms"),
                    "pages": payload.get("pages"),
                    "extracted": payload.get("extracted"),
                }
            )
    return rows


async def _run_trial(
    client: httpx.AsyncClient,
    *,
    trial_id: str,
    doc_count: int,
    pdf_bytes: bytes,
    timeout_s: float,
) -> dict[str, Any]:
    doc_ids = [f"doc-{uuid.uuid4().hex[:6]}" for _ in range(doc_count)]
    documents = _doc_defs(doc_ids)
    rules = _rules(doc_ids)
    workflow_id = f"wf-exp-{trial_id}-{uuid.uuid4().hex[:6]}"
    label = f"{trial_id} ({doc_count} doc)"

    save_res = await client.put(
        f"/v1/workflows/{workflow_id}",
        json={
            "id": workflow_id,
            "name": label,
            "description": "benchmark_extraction_experiments.py",
            "status": "draft",
            "owner": "benchmark",
            "documents": documents,
            "rules": rules,
        },
    )
    save_res.raise_for_status()

    snapshot = {"documents": documents, "rules": rules, "workflowName": label}
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

    wall_started = time.perf_counter()
    start_res = await client.post(
        f"/v1/workflows/{workflow_id}/runs/json",
        json={"snapshot": snapshot, "fileBindings": list(bindings)},
    )
    start_res.raise_for_status()
    run_id = start_res.json()["runId"]
    detail = await _poll_run(client, run_id, timeout_s=timeout_s)
    wall_ms = round((time.perf_counter() - wall_started) * 1000)

    result = detail["result"]
    metadata = result.get("metadata") or {}
    docs = result.get("documents") or []
    per_doc: list[dict[str, Any]] = []
    for doc in docs:
        ext = doc.get("extraction") or {}
        per_doc.append(
            {
                "extractionMs": ext.get("extractionMs"),
                "cacheHit": ext.get("cacheHit"),
                "documentType": doc.get("documentType"),
            }
        )

    vlm = _worker_vlm_timings(run_id)
    row = {
        "trial": trial_id,
        "docCount": doc_count,
        "runId": run_id,
        "wallMs": wall_ms,
        "durationMs": metadata.get("durationMs"),
        "extractionMs": metadata.get("extractionMs"),
        "validationMs": metadata.get("validationMs"),
        "perDoc": per_doc,
        "vlmTimings": vlm,
        "maxPromptMs": max((int(v.get("promptMs") or 0) for v in vlm), default=0),
        "sumPromptMs": sum(int(v.get("promptMs") or 0) for v in vlm),
        "sumPredictedMs": sum(int(v.get("predictedMs") or 0) for v in vlm),
        "status": result.get("status"),
    }

    try:
        await client.delete(f"/v1/workflows/{workflow_id}")
    except httpx.HTTPError:
        pass
    return row


def _print_row(row: dict[str, Any]) -> None:
    per = row.get("perDoc") or []
    per_ms = "+".join(str(d.get("extractionMs") or "-") for d in per)
    vlm = row.get("vlmTimings") or []
    vlm_s = ", ".join(
        f"p={v.get('promptMs')}/g={v.get('predictedMs')}" for v in vlm
    ) or "-"
    print(
        f"  {row['trial']:<28} wall={row.get('wallMs')}ms "
        f"duration={row.get('durationMs')}ms per-doc=[{per_ms}] "
        f"vlm=[{vlm_s}] cache={[d.get('cacheHit') for d in per]}"
    )


async def run_experiments(args: argparse.Namespace) -> int:
    pdf = args.document
    if not pdf.is_file():
        print(f"Missing PDF: {pdf}", file=sys.stderr)
        return 2

    token = _fetch_oidc_token(
        keycloak=args.keycloak,
        realm=args.realm,
        client_id=args.client_id,
        client_secret=args.client_secret,
        username=args.username,
        password=args.password,
    )
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    trials: list[tuple[str, int]] = []
    if args.trial in ("one-doc", "all"):
        trials.append(("one-doc-cold", 1))
    if args.trial in ("two-doc", "all"):
        trials.append(("two-doc-cold", 2))

    print(f"Extraction experiments @ {args.api}")
    print(f"  document: {pdf.name}")
    print(f"  trials: {[t[0] for t in trials]}")
    print("  (restart workers between configs, then re-run with --trial two-doc)")

    rows: list[dict[str, Any]] = []
    timeout = httpx.Timeout(args.timeout_seconds + 60, connect=15.0)
    async with httpx.AsyncClient(base_url=args.api.rstrip("/"), headers=headers, timeout=timeout) as client:
        pdf_bytes = pdf.read_bytes()
        for trial_id, doc_count in trials:
            print(f"\n[{trial_id}] running…", flush=True)
            try:
                row = await _run_trial(
                    client,
                    trial_id=trial_id,
                    doc_count=doc_count,
                    pdf_bytes=pdf_bytes,
                    timeout_s=args.timeout_seconds,
                )
            except Exception as exc:
                row = {"trial": trial_id, "docCount": doc_count, "error": str(exc)}
            rows.append(row)
            if row.get("error"):
                print(f"  FAILED: {row['error']}")
            else:
                _print_row(row)
            if args.pause_between_s > 0 and trial_id != trials[-1][0]:
                await asyncio.sleep(args.pause_between_s)

    report = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "api": args.api,
        "document": str(pdf),
        "configLabel": args.config_label or None,
        "results": rows,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport: {args.output}")
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--document", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--trial", choices=("one-doc", "two-doc", "all"), default="all")
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--pause-between-s", type=float, default=2.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "benchmark-reports" / "extraction-experiments.json",
    )
    parser.add_argument("--config-label", default="", help="Tag for worker config (e.g. parallel-off)")
    parser.add_argument("--keycloak", default="http://127.0.0.1:8080")
    parser.add_argument("--realm", default="repody")
    parser.add_argument("--client-id", default="repody-web")
    parser.add_argument("--client-secret", default="repody-web-dev-secret")
    parser.add_argument("--username", default="operator@repody.local")
    parser.add_argument("--password", default="repody-dev")
