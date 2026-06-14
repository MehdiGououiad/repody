"""Scoring and report helpers for document extraction benchmarks."""

from __future__ import annotations

import csv
import html
import io
import json
import re
import statistics
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any


def _amount(value: object) -> Decimal | None:
    raw = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not raw:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", raw)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        tail = cleaned.rsplit(",", 1)[-1]
        cleaned = cleaned.replace(",", ".") if len(tail) <= 2 else cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def normalize_text(value: object) -> str:
    folded = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join(folded.casefold().split())


def compare_value(
    actual: object,
    expected: object,
    *,
    comparison: str = "exact",
    tolerance: object = "0",
) -> bool:
    if comparison == "amount":
        actual_amount = _amount(actual)
        expected_amount = _amount(expected)
        tolerance_amount = _amount(tolerance) or Decimal("0")
        return (
            actual_amount is not None
            and expected_amount is not None
            and abs(actual_amount - expected_amount) <= tolerance_amount
        )
    if comparison == "contains":
        return normalize_text(expected) in normalize_text(actual)
    return normalize_text(actual) == normalize_text(expected)


def score_fields(
    actual_fields: dict[str, dict[str, Any]],
    expected_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    for expected in expected_fields:
        name = str(expected["name"])
        actual = actual_fields.get(name) or {}
        correct = bool(actual.get("extracted", True)) and compare_value(
            actual.get("value"),
            expected.get("expected"),
            comparison=str(expected.get("comparison") or "exact"),
            tolerance=expected.get("tolerance", "0"),
        )
        details.append(
            {
                "field": name,
                "expected": expected.get("expected"),
                "actual": actual.get("value"),
                "extracted": bool(actual.get("extracted", False)),
                "confidence": actual.get("confidence"),
                "correct": correct,
            }
        )
    correct_count = sum(1 for row in details if row["correct"])
    total = len(details)
    confidences = [
        float(row["confidence"])
        for row in details
        if isinstance(row.get("confidence"), (int, float))
    ]
    return {
        "correct": correct_count,
        "total": total,
        "accuracy": round(correct_count / total, 4) if total else 1.0,
        "meanConfidence": round(statistics.fmean(confidences), 4) if confidences else None,
        "details": details,
    }


def score_rules(
    actual_rules: list[dict[str, Any]],
    expected_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    by_id = {str(row.get("id") or ""): row for row in actual_rules}
    by_name = {str(row.get("name") or ""): row for row in actual_rules}
    details: list[dict[str, Any]] = []
    for expected in expected_rules:
        actual = by_id.get(str(expected.get("id") or "")) or by_name.get(
            str(expected.get("name") or "")
        )
        expected_status = str(expected.get("expectedStatus") or "passed")
        actual_status = str((actual or {}).get("status") or "missing")
        details.append(
            {
                "rule": expected.get("name") or expected.get("id"),
                "expected": expected_status,
                "actual": actual_status,
                "correct": actual_status == expected_status,
                "detail": (actual or {}).get("detail"),
            }
        )
    correct_count = sum(1 for row in details if row["correct"])
    total = len(details)
    return {
        "correct": correct_count,
        "total": total,
        "accuracy": round(correct_count / total, 4) if total else 1.0,
        "details": details,
    }


def csv_report(rows: list[dict[str, Any]]) -> str:
    columns = [
        "case",
        "model",
        "phase",
        "status",
        "passed",
        "wallMs",
        "queueMs",
        "durationMs",
        "extractionMs",
        "validationMs",
        "cacheHit",
        "fieldAccuracy",
        "ruleAccuracy",
        "readPathUsed",
        "error",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def html_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    rows = report["results"]

    def cell(value: object) -> str:
        if isinstance(value, float):
            return f"{value:.3f}"
        if value is None:
            return "-"
        return html.escape(str(value))

    table_rows = []
    for row in rows:
        status_class = "pass" if row.get("passed") else "skip" if row.get("skipped") else "fail"
        table_rows.append(
            "<tr>"
            f"<td>{cell(row.get('case'))}</td>"
            f"<td>{cell(row.get('model'))}</td>"
            f"<td>{cell(row.get('phase'))}</td>"
            f"<td class='{status_class}'>{cell(row.get('status'))}</td>"
            f"<td>{cell(row.get('wallMs'))}</td>"
            f"<td>{cell(row.get('queueMs'))}</td>"
            f"<td>{cell(row.get('extractionMs'))}</td>"
            f"<td>{cell(row.get('validationMs'))}</td>"
            f"<td>{cell(row.get('cacheHit'))}</td>"
            f"<td>{cell(row.get('fieldAccuracy'))}</td>"
            f"<td>{cell(row.get('ruleAccuracy'))}</td>"
            f"<td>{cell(row.get('error'))}</td>"
            "</tr>"
        )

    metadata = html.escape(json.dumps(report.get("environment", {}), indent=2, ensure_ascii=False))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentControl OCR benchmark</title>
<style>
:root {{ color-scheme: light dark; font-family: Inter, system-ui, sans-serif; }}
body {{ margin: 0; padding: 32px; background: #0b1020; color: #e8edf7; }}
main {{ max-width: 1500px; margin: auto; }}
h1 {{ margin-bottom: 4px; }}
.muted {{ color: #9aa7bd; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 12px; margin: 24px 0; }}
.card {{ background: #151d31; border: 1px solid #293551; border-radius: 12px; padding: 16px; }}
.value {{ font-size: 1.7rem; font-weight: 700; }}
.table-wrap {{ overflow-x: auto; border: 1px solid #293551; border-radius: 12px; }}
table {{ width: 100%; border-collapse: collapse; background: #11182a; }}
th, td {{ padding: 10px 12px; border-bottom: 1px solid #26314a; text-align: left; white-space: nowrap; }}
th {{ background: #19233a; position: sticky; top: 0; }}
.pass {{ color: #66e3a4; font-weight: 700; }}
.fail {{ color: #ff7d8d; font-weight: 700; }}
.skip {{ color: #f4c76b; font-weight: 700; }}
details {{ margin-top: 24px; }}
pre {{ overflow: auto; background: #11182a; border-radius: 12px; padding: 16px; }}
</style>
</head>
<body><main>
<h1>OCR benchmark report</h1>
<div class="muted">{cell(report.get("generatedAt"))} · {cell(report.get("profile"))}</div>
<section class="cards">
<div class="card"><div class="muted">Passed</div><div class="value">{summary["passed"]}</div></div>
<div class="card"><div class="muted">Failed</div><div class="value">{summary["failed"]}</div></div>
<div class="card"><div class="muted">Skipped</div><div class="value">{summary["skipped"]}</div></div>
<div class="card"><div class="muted">Field accuracy</div><div class="value">{summary["fieldAccuracy"]:.1%}</div></div>
<div class="card"><div class="muted">Rule accuracy</div><div class="value">{summary["ruleAccuracy"]:.1%}</div></div>
</section>
<div class="table-wrap"><table>
<thead><tr><th>Case</th><th>Model</th><th>Phase</th><th>Status</th><th>Wall ms</th>
<th>Queue ms</th><th>Extract ms</th><th>Validate ms</th><th>Cache</th>
<th>Field acc.</th><th>Rule acc.</th><th>Error</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody>
</table></div>
<details><summary>Environment</summary><pre>{metadata}</pre></details>
</main></body></html>"""
