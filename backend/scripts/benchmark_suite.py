#!/usr/bin/env python3
"""API-first OCR, extraction, and validation benchmark suite.

Dev-only tools (stress, queue, experiments): backend/scripts/benchmark_dev.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import statistics
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from audit_workbench.benchmarking import csv_report, html_report, score_fields, score_rules
from audit_workbench.catalog.registry import normalize_model_id

DEFAULT_MODELS = (
    "repody:vlm",
)

TEXT_PREVIEW_MAX_CHARS = 4_000


def _text_preview(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if len(stripped) <= TEXT_PREVIEW_MAX_CHARS:
        return stripped
    return f"{stripped[:TEXT_PREVIEW_MAX_CHARS]}\n\n… ({len(stripped):,} characters total)"


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    read_path: str
    validation_mode: str
    model: str | None
    fields_group: str = "fields"
    rules_group: str = "logicRules"
    repeated: bool = True


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _rule_payload(rows: list[dict[str, Any]], id_prefix: str) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        item = {key: value for key, value in row.items() if key != "expectedStatus"}
        item["id"] = f"{id_prefix}-rule-{index}"
        payload.append(item)
    return payload


def _field_payload(
    rows: list[dict[str, Any]],
    probe: str,
    id_prefix: str,
    *,
    include_probe: bool = True,
) -> list[dict[str, str]]:
    fields = [
        {
            "id": f"{id_prefix}-field-{index}",
            "name": str(row["name"]),
            "description": str(row.get("description") or ""),
        }
        for index, row in enumerate(rows, start=1)
    ]
    if include_probe:
        fields.append(
            {
                "id": f"{id_prefix}-field-probe",
                "name": probe,
                "description": "Benchmark cache-control probe; ignore if absent.",
            }
        )
    return fields


def _model_case_name(model: str) -> str:
    lower = model.casefold()
    if "repody-vlm" in lower or model == "repody:vlm":
        return "repody-vlm"
    token = model.split(":", 1)[-1].split("/")[-1]
    return "".join(char.lower() if char.isalnum() else "-" for char in token).strip("-")[:32]


def _cases(
    profile: str,
    models: list[str],
    model_validation: str,
) -> list[BenchmarkCase]:
    _ = model_validation
    cases: list[BenchmarkCase] = []
    if profile in {"quick", "full"}:
        cases.append(
            BenchmarkCase(
                "document-model-baseline",
                "document_model",
                "logic_only",
                "repody:vlm",
                "baselineFields",
            )
        )
    if profile in {"models", "full"}:
        cases.extend(
            BenchmarkCase(
                name=_model_case_name(model),
                read_path="document_model",
                validation_mode="logic_only",
                model=model,
                rules_group="logicRules",
            )
            for model in models
        )
    if profile == "full":
        cases.extend(
            [
                BenchmarkCase(
                    "logic-validation",
                    "document_model",
                    "logic_only",
                    "repody:vlm",
                    "baselineFields",
                    "logicValidationRules",
                    repeated=False,
                ),
            ]
        )
    return cases


async def _get_json(client: httpx.AsyncClient, path: str) -> dict[str, Any]:
    response = await client.get(path)
    if response.is_error:
        raise RuntimeError(f"{response.request.method} {path} failed {response.status_code}: {response.text[:500]}")
    return response.json()


def _client_headers(bearer_token: str | None) -> dict[str, str]:
    if not bearer_token:
        return {}
    return {"Authorization": f"Bearer {bearer_token}"}


async def _save_workflow(
    client: httpx.AsyncClient,
    *,
    workflow_id: str,
    case: BenchmarkCase,
    document: dict[str, Any],
    rules: list[dict[str, Any]],
) -> None:
    response = await client.put(
        f"/v1/workflows/{workflow_id}",
        json={
            "id": workflow_id,
            "name": f"Benchmark · {case.name}",
            "description": "Temporary workflow created by benchmark_suite.py",
            "status": "draft",
            "owner": "benchmark-suite",
            "documents": [document],
            "rules": rules,
        },
    )
    if response.is_error:
        raise RuntimeError(
            f"PUT /v1/workflows/{workflow_id} failed {response.status_code}: "
            f"{response.text[:500]}"
        )


async def _poll(
    client: httpx.AsyncClient,
    run_id: str,
    *,
    timeout_s: float,
) -> tuple[dict[str, Any], int]:
    deadline = time.monotonic() + timeout_s
    polls = 0
    delay = 0.3
    while time.monotonic() < deadline:
        polls += 1
        status = await _get_json(client, f"/v1/runs/{run_id}/status")
        if status.get("status") == "failed":
            raise RuntimeError(str(status.get("error") or "Run failed"))
        if status.get("status") == "done":
            detail = await _get_json(client, f"/v1/runs/{run_id}")
            if not detail.get("result"):
                raise RuntimeError("Run completed without an audit result")
            return detail, polls
        await asyncio.sleep(delay)
        delay = min(1.5, delay + 0.15)
    raise TimeoutError(f"Run {run_id} exceeded {timeout_s:.0f}s")


async def _run_once(
    client: httpx.AsyncClient,
    *,
    suite_id: str,
    case: BenchmarkCase,
    phase: str,
    workflow_id: str,
    manifest: dict[str, Any],
    document_bytes: bytes,
    filename: str,
    timeout_s: float,
    probe: str,
    expect_cache: bool | None,
    minimum_accuracy: float,
    judge_quality: bool,
) -> dict[str, Any]:
    document_id = f"doc-{suite_id}-{case.name}"
    case_token = "".join(char for char in case.name if char.isalnum())[:4]
    id_prefix = f"b{suite_id}{case_token}"
    expected_fields = list(manifest.get(case.fields_group) or manifest.get("fields") or [])
    expected_rules = list(manifest.get(case.rules_group) or [])
    schema = _field_payload(
        expected_fields,
        probe,
        id_prefix,
        # Phase-specific probe isolates Redis cache keys (required for markdown-only docs).
        include_probe=True,
    )
    document: dict[str, Any] = {
        "id": document_id,
        "documentType": manifest.get("documentType") or "Document",
        "extractionMode": case.read_path,
        "validationMode": case.validation_mode,
        "schema": schema,
    }
    if case.model:
        document["ocrModel"] = case.model
    if judge_quality:
        document["markdownExtraction"] = True
    rules = _rule_payload(expected_rules, id_prefix)
    await _save_workflow(
        client,
        workflow_id=workflow_id,
        case=case,
        document=document,
        rules=rules,
    )

    payload = json.dumps(
        {
            "documents": [document],
            "rules": rules,
            "workflowName": f"Benchmark · {case.name}",
        }
    )
    multipart = [
        ("payload", (None, payload.encode(), "application/json")),
        ("document_ids", (None, json.dumps([document_id]).encode(), "application/json")),
        (
            "files",
            (
                filename,
                document_bytes,
                str(manifest.get("mimeType") or "application/pdf"),
            ),
        ),
    ]
    wall_started = time.perf_counter()
    submit_started = time.perf_counter()
    response = await client.post(
        f"/v1/workflows/{workflow_id}/runs",
        files=multipart,
    )
    submit_ms = round((time.perf_counter() - submit_started) * 1000)
    if response.is_error:
        raise RuntimeError(
            f"POST run failed {response.status_code}: {response.text[:500]}"
        )
    run_id = response.json()["runId"]
    detail, polls = await _poll(client, run_id, timeout_s=timeout_s)
    wall_ms = round((time.perf_counter() - wall_started) * 1000)
    result = detail["result"]
    metadata = result.get("metadata") or {}
    document_result = (result.get("documents") or [{}])[0]
    extraction = document_result.get("extraction") or {}
    fields = {
        str(row.get("key")): row
        for row in document_result.get("fields") or []
        if row.get("key")
    }
    field_score = score_fields(fields, expected_fields)
    rule_score = score_rules(result.get("ruleResults") or [], expected_rules)
    raw_text = str(extraction.get("rawText") or document_result.get("rawText") or "")
    raw_text_chars = len(raw_text.strip())
    ocr_text = str(extraction.get("ocrText") or "")
    ocr_text_chars = len(ocr_text.strip())
    created_at = _parse_dt(result.get("createdAt"))
    started_at = _parse_dt(metadata.get("startedAt"))
    queue_ms = None
    if created_at and started_at:
        queue_ms = max(0, round((started_at - created_at).total_seconds() * 1000))
    cache_hit = bool(extraction.get("cacheHit"))
    cache_ok = expect_cache is None or cache_hit is expect_cache
    if judge_quality:
        text_chars = ocr_text_chars
        text_preview = _text_preview(ocr_text)
        passed = text_chars > 0 and cache_ok
        error = None
        if not cache_ok:
            error = f"Expected cacheHit={expect_cache}, received {cache_hit}"
        elif text_chars == 0:
            error = "NuExtract markdown output was empty"
    elif ocr_compare:
        text_preview = _text_preview(raw_text)
        passed = raw_text_chars > 0 and cache_ok
        error = None
        if not cache_ok:
            error = f"Expected cacheHit={expect_cache}, received {cache_hit}"
        elif raw_text_chars == 0:
            error = "OCR compare model produced no text"
    else:
        text_preview = _text_preview(ocr_text) if ocr_text_chars else _text_preview(raw_text)
        passed = (
            field_score["accuracy"] >= minimum_accuracy
            and rule_score["accuracy"] == 1.0
            and cache_ok
        )
        error = None
        if not cache_ok:
            error = f"Expected cacheHit={expect_cache}, received {cache_hit}"
        elif field_score["accuracy"] < minimum_accuracy:
            error = (
                f"Field accuracy {field_score['accuracy']:.1%} is below "
                f"{minimum_accuracy:.1%}"
            )
        elif rule_score["accuracy"] < 1.0:
            error = f"Rule accuracy {rule_score['accuracy']:.1%} is below 100%"

    return {
        "case": case.name,
        "model": case.model or case.read_path,
        "phase": phase,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "skipped": False,
        "ocrCompare": ocr_compare,
        "judgeQuality": judge_quality,
        "runId": run_id,
        "wallMs": wall_ms,
        "submitMs": submit_ms,
        "queueMs": queue_ms,
        "durationMs": metadata.get("durationMs"),
        "extractionMs": metadata.get("extractionMs"),
        "validationMs": metadata.get("validationMs"),
        "polls": polls,
        "cacheHit": cache_hit,
        "readPathUsed": extraction.get("readPathUsed"),
        "fieldsExtracted": extraction.get("fieldsExtracted"),
        "rawTextChars": raw_text_chars,
        "ocrTextChars": ocr_text_chars,
        "textPreview": text_preview if (judge_quality or ocr_compare) else None,
        "fieldAccuracy": field_score["accuracy"],
        "ruleAccuracy": rule_score["accuracy"],
        "fieldScore": field_score,
        "ruleScore": rule_score,
        "error": error,
    }


def _skip_row(case: BenchmarkCase, reason: str) -> dict[str, Any]:
    return {
        "case": case.name,
        "model": case.model or case.read_path,
        "phase": "availability",
        "status": "skipped",
        "passed": False,
        "skipped": True,
        "fieldAccuracy": 0.0,
        "ruleAccuracy": 0.0,
        "error": reason,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [row for row in rows if not row.get("skipped")]
    structured = [
        row
        for row in measured
        if not row.get("ocrCompare") and not row.get("judgeQuality")
    ]
    field_total = sum(int((row.get("fieldScore") or {}).get("total") or 0) for row in structured)
    field_correct = sum(int((row.get("fieldScore") or {}).get("correct") or 0) for row in structured)
    rule_total = sum(int((row.get("ruleScore") or {}).get("total") or 0) for row in structured)
    rule_correct = sum(int((row.get("ruleScore") or {}).get("correct") or 0) for row in structured)
    wall_times = [int(row["wallMs"]) for row in measured if isinstance(row.get("wallMs"), int)]
    ocr_rows = [row for row in measured if row.get("ocrCompare")]
    return {
        "passed": sum(1 for row in measured if row.get("passed")),
        "failed": sum(1 for row in measured if not row.get("passed")),
        "skipped": sum(1 for row in rows if row.get("skipped")),
        "fieldAccuracy": round(field_correct / field_total, 4) if field_total else 1.0,
        "ruleAccuracy": round(rule_correct / rule_total, 4) if rule_total else 1.0,
        "medianWallMs": round(statistics.median(wall_times)) if wall_times else None,
        "ocrCompareRuns": len(ocr_rows),
        "medianRawTextChars": round(statistics.median(
            [int(row.get("rawTextChars") or 0) for row in ocr_rows]
        )) if ocr_rows else None,
    }


def _print_table(rows: list[dict[str, Any]]) -> None:
    headers = (
        "case",
        "phase",
        "status",
        "wall",
        "queue",
        "extract",
        "validate",
        "cache",
        "fields",
        "rules",
        "ocr-chars",
    )
    print("\n" + " | ".join(f"{header:>10}" for header in headers))
    print("-" * 145)
    for row in rows:
        field_display = (
            "-"
            if row.get("ocrCompare")
            else f"{float(row.get('fieldAccuracy') or 0):.0%}"
        )
        rule_display = (
            "-"
            if row.get("ocrCompare")
            else f"{float(row.get('ruleAccuracy') or 0):.0%}"
        )
        values = (
            str(row.get("case") or "")[:18],
            str(row.get("phase") or ""),
            str(row.get("status") or ""),
            str(row.get("wallMs") or "-"),
            str(row.get("queueMs") if row.get("queueMs") is not None else "-"),
            str(row.get("extractionMs") if row.get("extractionMs") is not None else "-"),
            str(row.get("validationMs") if row.get("validationMs") is not None else "-"),
            str(row.get("cacheHit") if row.get("cacheHit") is not None else "-"),
            field_display,
            rule_display,
            str(row.get("rawTextChars") if row.get("ocrCompare") else "-"),
        )
        print(" | ".join(f"{value:>10}" for value in values))


async def _execute_benchmark_case(
    client: httpx.AsyncClient,
    *,
    args: argparse.Namespace,
    suite_id: str,
    case: BenchmarkCase,
    manifest: dict[str, Any],
    document_bytes: bytes,
    filename: str,
    availability: dict[str, dict[str, Any]],
    cache_enabled: bool,
) -> list[dict[str, Any]]:
    case_rows: list[dict[str, Any]] = []
    model_info = availability.get(case.model or "") if case.model else None
    if case.model and model_info and not model_info.get("available", False):
        reason = str(model_info.get("availabilityNote") or "Model is unavailable")
        case_rows.append(_skip_row(case, reason))
        print(f"[SKIP] {case.name}: {reason}", flush=True)
        return case_rows

    workflow_id = f"wf-benchmark-{suite_id}-{case.name}"
    print(f"\n[{case.name}] {case.model or case.read_path}", flush=True)
    try:
        phase_specs: list[tuple[str, str, bool | None]] = [
            ("first", f"_benchmark_probe_{suite_id}_{case.name}_first", False)
        ]
        if case.repeated:
            for index in range(args.warm_runs):
                phase_specs.append(
                    (
                        f"warm-{index + 1}",
                        f"_benchmark_probe_{suite_id}_{case.name}_warm_{index + 1}",
                        False,
                    )
                )
            if args.cache_check and cache_enabled:
                last_probe = phase_specs[-1][1]
                phase_specs.append(("cache", last_probe, True))

        for phase, probe, expect_cache in phase_specs:
            started = time.perf_counter()
            try:
                row = await _run_once(
                    client,
                    suite_id=suite_id,
                    case=case,
                    phase=phase,
                    workflow_id=workflow_id,
                    manifest=manifest,
                    document_bytes=document_bytes,
                    filename=filename,
                    timeout_s=args.timeout_seconds,
                    probe=probe,
                    expect_cache=expect_cache,
                    minimum_accuracy=args.minimum_accuracy,
                    judge_quality=args.judge_quality,
                )
            except Exception as exc:
                row = {
                    "case": case.name,
                    "model": case.model or case.read_path,
                    "phase": phase,
                    "status": "failed",
                    "passed": False,
                    "skipped": False,
                    "wallMs": round((time.perf_counter() - started) * 1000),
                    "fieldAccuracy": 0.0,
                    "ruleAccuracy": 0.0,
                    "error": str(exc),
                }
            case_rows.append(row)
            field_display = (
                str(row.get("rawTextChars") or "-")
                if row.get("ocrCompare")
                else f"{float(row.get('fieldAccuracy') or 0):.0%}"
            )
            print(
                f"  {phase:<8} {row['status']:<7} "
                f"wall={row.get('wallMs', '-')}ms "
                f"extract={row.get('extractionMs', '-')}ms "
                f"score={field_display}",
                flush=True,
            )
            if not row.get("passed") and not args.continue_on_failure:
                break
    finally:
        try:
            await client.delete(f"/v1/workflows/{workflow_id}")
        except Exception:
            pass
    return case_rows


def _parallel_model_cases(profile: str, cases: list[BenchmarkCase]) -> list[BenchmarkCase]:
    if profile not in {"models", "full"}:
        return []
    return [case for case in cases if case.model]


async def run(args: argparse.Namespace) -> int:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    document_bytes = args.document.read_bytes()
    suite_id = uuid.uuid4().hex[:8]
    generated_at = datetime.now(UTC).isoformat()
    timeout = httpx.Timeout(connect=10.0, read=args.timeout_seconds + 30, write=60.0, pool=10.0)
    rows: list[dict[str, Any]] = []

    async with httpx.AsyncClient(
        base_url=args.api.rstrip("/"),
        timeout=timeout,
        limits=httpx.Limits(max_connections=16, max_keepalive_connections=8),
        headers=_client_headers(args.bearer_token),
    ) as client:
        try:
            health = await _get_json(client, "/v1/healthz")
            environment = {
                "health": health,
                "modelsCatalog": await _get_json(client, "/v1/models/catalog"),
            }
            try:
                environment["platform"] = await _get_json(client, "/v1/platform/config")
            except Exception:
                environment["platform"] = {"cacheEnabled": bool(health.get("cacheEnabled"))}
        except Exception as exc:
            print(f"Benchmark cannot reach the Docker API at {args.api}: {exc}", file=sys.stderr)
            return 2

        availability = {
            str(model.get("id")): model
            for model in environment["modelsCatalog"].get("models") or []
        }
        cache_enabled = bool(
            environment["platform"].get("cacheEnabled", health.get("cacheEnabled"))
        )
        cases = _cases(
            args.profile,
            args.model or list(DEFAULT_MODELS),
            args.model_validation,
        )
        parallel_cases = _parallel_model_cases(args.profile, cases)
        parallel_ids = {case.name for case in parallel_cases}
        sequential_cases = [case for case in cases if case.name not in parallel_ids]

        for case in sequential_cases:
            rows.extend(
                await _execute_benchmark_case(
                    client,
                    args=args,
                    suite_id=suite_id,
                    case=case,
                    manifest=manifest,
                    document_bytes=document_bytes,
                    filename=args.document.name,
                    availability=availability,
                    cache_enabled=cache_enabled,
                )
            )

        if parallel_cases:
            print(
                f"\nRunning {len(parallel_cases)} model case(s) in parallel…",
                flush=True,
            )
            semaphore = asyncio.Semaphore(min(4, len(parallel_cases)))

            async def _bounded(case: BenchmarkCase) -> list[dict[str, Any]]:
                async with semaphore:
                    return await _execute_benchmark_case(
                        client,
                        args=args,
                        suite_id=suite_id,
                        case=case,
                        manifest=manifest,
                        document_bytes=document_bytes,
                        filename=args.document.name,
                        availability=availability,
                        cache_enabled=cache_enabled,
                    )

            parallel_results = await asyncio.gather(
                *[_bounded(case) for case in parallel_cases]
            )
            for case_rows in parallel_results:
                rows.extend(case_rows)

    summary = _summary(rows)
    report = {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "suiteId": suite_id,
        "profile": args.profile,
        "document": {
            "path": str(args.document),
            "bytes": len(document_bytes),
            "manifest": str(args.manifest),
            "name": manifest.get("name") or args.document.name,
        },
        "settings": {
            "warmRuns": args.warm_runs,
            "cacheCheck": args.cache_check,
            "minimumAccuracy": args.minimum_accuracy,
            "judgeQuality": args.judge_quality,
            "timeoutSeconds": args.timeout_seconds,
            "strictModels": args.strict_models,
        },
        "environment": environment,
        "summary": summary,
        "results": rows,
    }
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    report_dir = args.output_dir / f"{stamp}-{suite_id}"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "benchmark-report.json"
    html_path = report_dir / "benchmark-report.html"
    csv_path = report_dir / "benchmark-results.csv"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    html_path.write_text(html_report(report), encoding="utf-8")
    csv_path.write_text(csv_report(rows), encoding="utf-8")
    for source, name in (
        (json_path, "latest.json"),
        (html_path, "latest.html"),
        (csv_path, "latest.csv"),
    ):
        shutil.copyfile(source, args.output_dir / name)

    _print_table(rows)
    print(
        f"\nSummary: {summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['skipped']} skipped; field accuracy={summary['fieldAccuracy']:.1%}, "
        f"rule accuracy={summary['ruleAccuracy']:.1%}"
    )
    print(f"Reports: {report_dir}")

    unavailable_failure = args.strict_models and summary["skipped"] > 0
    return 1 if summary["failed"] > 0 or unavailable_failure else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark document models through the same multipart API flow used by the UI."
    )
    parser.add_argument("--api", default="http://api:8000")
    parser.add_argument(
        "--bearer-token",
        default=os.environ.get("AUDIT_BENCHMARK_BEARER_TOKEN"),
        help="OIDC bearer token for authenticated management API calls.",
    )
    parser.add_argument(
        "--document",
        type=Path,
        default=Path("/app/e2e/fixtures/documents/Facture.pdf"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("/app/e2e/fixtures/documents/Facture.benchmark.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("/app/benchmark-reports"))
    parser.add_argument("--profile", choices=("quick", "models", "full"), default="full")
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument(
        "--model-validation",
        choices=("logic_only",),
        default="logic_only",
        help="Validation mode used by document-model benchmark cases.",
    )
    parser.add_argument("--warm-runs", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--minimum-accuracy", type=float, default=1.0)
    parser.add_argument(
        "--judge-quality",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="NuExtract markdown/text quality check; pass when text output is non-empty.",
    )
    parser.add_argument("--strict-models", action="store_true")
    parser.add_argument("--continue-on-failure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cache-check", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    if not args.document.is_file():
        parser.error(f"Document not found: {args.document}")
    if not args.manifest.is_file():
        parser.error(f"Manifest not found: {args.manifest}")
    if args.warm_runs < 0:
        parser.error("--warm-runs must be at least 0")
    if not 0 <= args.minimum_accuracy <= 1:
        parser.error("--minimum-accuracy must be between 0 and 1")
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
