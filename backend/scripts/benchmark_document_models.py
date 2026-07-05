#!/usr/bin/env python3
"""Benchmark production document-model adapters on one file."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from pathlib import Path

os.environ["AUDIT_EXTRACTION_CACHE_ENABLED"] = "false"

from audit_workbench.extraction.base import SchemaFieldSpec  # noqa: E402
from audit_workbench.extraction.pipeline import PipelineExtractor  # noqa: E402

DEFAULT_MODELS = (
    "repody:vlm",
)


async def _run_model(
    model: str,
    document: bytes,
    mime_type: str,
    schema: list[SchemaFieldSpec],
    document_type: str,
    runs: int,
) -> dict[str, object]:
    timings: list[float] = []
    last = None
    error: str | None = None
    for _ in range(runs):
        started = time.perf_counter()
        try:
            last = await PipelineExtractor().extract(
                document,
                mime_type,
                document_type,
                schema,
                extraction_mode="document_model",
                validation_mode="logic_only",
                document_model_id=model,
            )
            timings.append(time.perf_counter() - started)
        except Exception as exc:
            timings.append(time.perf_counter() - started)
            error = repr(exc)
            break

    fields = {
        field.key: {
            "value": field.value,
            "confidence": field.confidence,
            "extracted": field.extracted,
        }
        for field in (last.fields if last else [])
    }
    return {
        "model": model,
        "ok": error is None and bool(last),
        "runs": len(timings),
        "median_seconds": round(statistics.median(timings), 3),
        "min_seconds": round(min(timings), 3),
        "max_seconds": round(max(timings), 3),
        "fields": fields,
        "raw_text_chars": len(last.raw_text or "") if last else 0,
        "error": error,
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--mime-type", default="application/pdf")
    parser.add_argument("--document-type", default="Invoice")
    parser.add_argument("--field", action="append", default=[])
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()

    fields = args.field or [
        "total_amount:Total TTC including tax",
        "tax_amount:Total TVA tax amount",
        "subtotal_amount:Total HT before tax",
    ]
    schema = [
        SchemaFieldSpec(name=name.strip(), description=description.strip())
        for name, _, description in (field.partition(":") for field in fields)
        if name.strip()
    ]
    document = args.document.read_bytes()
    rows = []
    for model in args.model or DEFAULT_MODELS:
        row = await _run_model(
            model,
            document,
            args.mime_type,
            schema,
            args.document_type,
            max(1, args.runs),
        )
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return 0 if all(bool(row["ok"]) for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
