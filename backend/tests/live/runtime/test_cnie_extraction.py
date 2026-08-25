"""Live CNIE structured extraction against Gououiad fixtures + ground truth.

Uses the recommended UI path: presign → PUT → confirm → runs/json.
Schema fields mirror gououiad-cnie.ocr-expectations.json (recto + verso).

Requires running stack (API + extract worker + llamacpp) and auth:

  $env:E2E_API_URL = "http://127.0.0.1:8000"
  $env:E2E_AUTH_URL = "http://127.0.0.1:8080"
  $env:E2E_STACK = "1"
  pnpm test:api:live -- tests/live/platform/test_cnie_extraction.py -v -s
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest

from repody.benchmarking import score_gououiad_cnie_fields
from repody.extraction.branding import REPODY_VLM_CATALOG_ID
from repody.infra.storage.mime import JPEG, PDF, PNG, WEBP, resolve_mime
from repody.integration.live_stack import (
    create_live_async_client,
    live_api_base,
)
from repody.integration.workflow_flow import run_test_with_files, save_workflow

pytestmark = [pytest.mark.live, pytest.mark.slow]

FIXTURES = Path(__file__).resolve().parents[4] / "e2e" / "fixtures" / "documents"
FRONT_PATH = FIXTURES / "gououiad-cnie-front.png"
BACK_PATH = FIXTURES / "gououiad-cnie-back.png"
EXPECTATIONS_PATH = FIXTURES / "gououiad-cnie.ocr-expectations.json"

MIN_CORE_RATIO = 0.55

_MIME_EXT = {
    JPEG: ".jpg",
    PNG: ".png",
    WEBP: ".webp",
    PDF: ".pdf",
}


def _file_for_presign(path: Path) -> tuple[str, bytes, str]:
    """Filename + bytes + sniffed MIME (confirm rejects extension/MIME lies)."""
    data = path.read_bytes()
    mime = resolve_mime(data=data, declared=None)
    ext = _MIME_EXT.get(mime)
    name = f"{path.stem}{ext}" if ext else path.name
    return name, data, mime


def _schema_from_side(side: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in (side.get("core_fields") or []) + (side.get("hard_fields") or []):
        field_id = str(field["id"])
        template = "verbatim-string"
        if field_id in {"dob_full", "valid_2035"}:
            template = "date"
        rows.append(
            {
                "id": f"f-{field_id}",
                "name": field_id,
                "description": str(field.get("label") or field_id),
                "templateType": template,
            }
        )
    return rows


def _doc(
    doc_id: str,
    *,
    label: str,
    side: dict[str, Any],
    instructions: str,
) -> dict[str, Any]:
    return {
        "id": doc_id,
        "documentType": label,
        "schema": _schema_from_side(side),
        "extractionMode": "document_model",
        "validationMode": "logic_only",
        "documentModelId": REPODY_VLM_CATALOG_ID,
        "markdownExtraction": False,
        "extractionInstructions": instructions,
    }


def _fields_map(doc: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in doc.get("fields") or []:
        key = field.get("key") or field.get("name")
        if not key:
            continue
        value = field.get("value")
        out[str(key)] = "" if value is None else str(value)
    return out


FRONT_INSTRUCTIONS = (
    "Moroccan CNIE recto (carte nationale d'identité). "
    "Extract Latin and Arabic identity fields exactly as printed: "
    "national_id (CIN / N°), first_name, last_name, date of birth, "
    "validity date, CAN serial, birth place, document title, kingdom header."
)

BACK_INSTRUCTIONS = (
    "Moroccan CNIE verso. Extract parent names, address, gender, "
    "état civil number, OPI code, and all three MRZ lines exactly as printed."
)


async def _prime_and_time(
    client: httpx.AsyncClient,
    *,
    wf_id: str,
    front_id: str,
    front_file: tuple[str, bytes, str],
    front_side: dict[str, Any],
) -> dict[str, Any]:
    # Small structured prime so the warm path matches timed structured extract.
    prime_side = {
        "core_fields": [
            f
            for f in (front_side.get("core_fields") or [])
            if f.get("id") in {"national_id", "first_name", "last_name"}
        ],
        "hard_fields": [],
    }
    documents = [
        _doc(
            front_id,
            label="CNIE Recto (prime)",
            side=prime_side,
            instructions=FRONT_INSTRUCTIONS,
        )
    ]
    await save_workflow(
        client,
        wf_id=wf_id,
        name="CNIE Gououiad live (prime)",
        documents=documents,
        rules=[],
        owner="e2e",
    )
    started = time.perf_counter()
    result = await run_test_with_files(
        client,
        wf_id,
        documents=documents,
        rules=[],
        workflow_name="CNIE Gououiad live (prime)",
        files_by_doc_id={front_id: front_file},
        max_wait_ms=900_000,
    )
    return {
        "primeWallMs": int((time.perf_counter() - started) * 1000),
        "runId": result.get("id"),
        "auditId": result.get("id"),
        "status": result.get("status"),
        "extractionMs": (result.get("metadata") or {}).get("extractionMs")
        or (result.get("metadata") or {}).get("extraction_ms"),
        "fieldsExtracted": (result.get("summary") or {}).get("fieldsExtracted"),
        "uploadPath": "presign",
        "mode": "structured",
    }


def _print_report(report: dict[str, Any]) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=True)[:12000]
    print("\n======== CNIE LIVE STRUCTURED EXTRACTION REPORT ========")
    print(payload)
    print("========================================================\n")


@pytest.mark.asyncio
async def test_gououiad_cnie_structured_extraction_after_warmup():
    if not FRONT_PATH.is_file() or not BACK_PATH.is_file():
        pytest.skip(f"CNIE fixtures missing under {FIXTURES}")
    if not EXPECTATIONS_PATH.is_file():
        pytest.skip(f"ground truth missing: {EXPECTATIONS_PATH}")

    expectations = json.loads(EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    front_side = expectations["front"]
    back_side = expectations["back"]

    async with create_live_async_client() as client:
        health = (await client.get("/v1/healthz")).json()
        assert health.get("status") == "ok"

        created = await client.post(
            "/v1/workflows",
            json={
                "name": "CNIE Gououiad structured",
                "description": "carte nationale structured e2e",
                "owner": "e2e",
            },
        )
        created.raise_for_status()
        wf_id = created.json()["workflow"]["id"]
        front_id = f"cnie-front-{uuid.uuid4().hex[:8]}"
        back_id = f"cnie-back-{uuid.uuid4().hex[:8]}"
        front_file = _file_for_presign(FRONT_PATH)
        back_file = _file_for_presign(BACK_PATH)
        assert front_file[2] == JPEG, f"expected JPEG bytes in front fixture, got {front_file[2]}"
        assert back_file[2] == JPEG, f"expected JPEG bytes in back fixture, got {back_file[2]}"

        prime = await _prime_and_time(
            client,
            wf_id=wf_id,
            front_id=f"{front_id}-prime",
            front_file=front_file,
            front_side=front_side,
        )

        documents = [
            _doc(
                front_id,
                label="CNIE Recto",
                side=front_side,
                instructions=FRONT_INSTRUCTIONS,
            ),
            _doc(
                back_id,
                label="CNIE Verso",
                side=back_side,
                instructions=BACK_INSTRUCTIONS,
            ),
        ]
        await save_workflow(
            client,
            wf_id=wf_id,
            name="CNIE Gououiad structured",
            documents=documents,
            rules=[],
            owner="e2e",
        )

        extract_started = time.perf_counter()
        result = await run_test_with_files(
            client,
            wf_id,
            documents=documents,
            rules=[],
            workflow_name="CNIE Gououiad structured",
            files_by_doc_id={
                front_id: front_file,
                back_id: back_file,
            },
            max_wait_ms=900_000,
        )
        extract_wall_ms = int((time.perf_counter() - extract_started) * 1000)

        docs = result.get("documents") or []
        assert len(docs) >= 2, f"expected 2 documents, got {len(docs)}: {docs}"
        front_doc = next((d for d in docs if d.get("id") == front_id), None) or docs[0]
        back_doc = next((d for d in docs if d.get("id") == back_id), None) or docs[1]
        front_fields = _fields_map(front_doc)
        back_fields = _fields_map(back_doc)
        assert front_fields, "front structured fields empty"
        assert back_fields, "back structured fields empty"

        scored = score_gououiad_cnie_fields(front_fields, back_fields, include_hard=True)
        meta = result.get("metadata") or {}
        front_ext = front_doc.get("extraction") or {}
        back_ext = back_doc.get("extraction") or {}
        run_id = result.get("id")

        report = {
            "api": live_api_base(),
            "uploadPath": "presign",
            "mode": "structured",
            "fixtures": {
                "front": str(FRONT_PATH),
                "back": str(BACK_PATH),
                "groundTruth": str(EXPECTATIONS_PATH),
                "declaredMime": {"front": front_file[2], "back": back_file[2]},
                "uploadNames": {"front": front_file[0], "back": back_file[0]},
                "schemaFieldCounts": {
                    "front": len(documents[0]["schema"]),
                    "back": len(documents[1]["schema"]),
                },
            },
            "timing": {
                "primeExtract": prime,
                "extractWallMs": extract_wall_ms,
                "runDurationMs": meta.get("durationMs") or meta.get("duration_ms"),
                "runExtractionMs": meta.get("extractionMs") or meta.get("extraction_ms"),
                "frontExtractionMs": front_ext.get("extractionMs")
                or front_ext.get("extraction_ms"),
                "backExtractionMs": back_ext.get("extractionMs") or back_ext.get("extraction_ms"),
                "frontCacheHit": front_ext.get("cacheHit") or front_ext.get("cache_hit"),
                "backCacheHit": back_ext.get("cacheHit") or back_ext.get("cache_hit"),
                "note": (
                    "structured CNIE via presign→confirm→runs/json after prime; "
                    "compare frontExtractionMs/backExtractionMs to ~10s Facture baseline"
                ),
            },
            "run": {
                "runId": run_id,
                "auditId": result.get("id"),
                "status": result.get("status"),
                "fieldsExtracted": (result.get("summary") or {}).get("fieldsExtracted"),
            },
            "groundTruthScore": {
                "total": f"{scored['total_score']}/{scored['total_max']}",
                "core": f"{scored['core_score']}/{scored['core_max']}",
                "hard": f"{scored['hard_score']}/{scored['hard_max']}",
                "cinHit": scored["cin_hit"],
                "mrzHit": scored["mrz_hit"],
                "primaryHit": scored["primary_hit"],
                "hits": scored["hits"],
            },
            "extractedFields": {
                "front": front_fields,
                "back": back_fields,
            },
        }
        out = Path(__file__).resolve().parents[4] / "benchmark-reports" / "cnie-live-last.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        _print_report(report)

        core_max = max(1, int(scored["core_max"]))
        core_ratio = float(scored["core_score"]) / core_max
        assert scored["cin_hit"], (
            f"CIN ground truth miss; fields={front_fields} hits={scored['hits']}"
        )
        assert core_ratio >= MIN_CORE_RATIO, (
            f"core score too low: {scored['core_score']}/{scored['core_max']} "
            f"(ratio={core_ratio:.2f}); fields front={front_fields} back={back_fields}"
        )
