#!/usr/bin/env python3
"""Full Gououiad CNIE benchmark — all document-model extraction paths.

Scores recto+verso against e2e/fixtures/documents/gououiad-cnie.ocr-expectations.json.

Paths:
  - repody:vlm markdown
  - repody:vlm structured (NuExtract field extraction)
  - paddleocr:v6 markdown
  - paddleocr:qwen structured (PP-OCRv6 + Qwen text→JSON)
  - glm:ocr markdown (official SDK profile)
  - glm:qwen structured (GLM-OCR SDK + Qwen text→JSON)
  - glm:ocr markdown + ID-card profile (optional extension)

Usage (host, services on :8081 / :8083 / :8084 / :8868):

  cd backend
  uv run python scripts/benchmark_gououiad_cnie.py

  uv run python scripts/benchmark_gououiad_cnie.py --skip-glm-id-card
  uv run python scripts/benchmark_gououiad_cnie.py --only paddleocr:qwen,glm:qwen,repody:vlm:structured
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from repody.benchmarking import score_gououiad_cnie_fields, score_gououiad_cnie_markdown
from repody.extraction.branding import (
    GLM_OCR_CATALOG_ID,
    GLM_OCR_QWEN_CATALOG_ID,
    PADDLEOCR_QWEN_CATALOG_ID,
    PADDLEOCR_V6_CATALOG_ID,
    REPODY_VLM_CATALOG_ID,
)
from repody.extraction.glm_ocr import extract_with_glm_ocr
from repody.extraction.glm_ocr_qwen import extract_with_glm_ocr_qwen
from repody.extraction.glm_ocr_sdk import reset_glm_ocr_sdk_client
from repody.extraction.paddleocr_qwen import extract_with_paddleocr_qwen
from repody.extraction.paddleocr_v6 import extract_with_paddleocr_v6
from repody.extraction.types import DocumentBundle, SchemaFieldSpec
from repody.extraction.vlm import extract_with_repody_vlm
from repody.infra.storage.mime import resolve_mime
from repody.integration.fixtures import repo_root
from repody.settings import get_settings

FIXTURES = repo_root() / "e2e" / "fixtures" / "documents"
FRONT_PATH = FIXTURES / "gououiad-cnie-front.png"
BACK_PATH = FIXTURES / "gououiad-cnie-back.png"
EXPECTATIONS_PATH = FIXTURES / "gououiad-cnie.ocr-expectations.json"
DEFAULT_REPORT = repo_root() / "benchmark-reports" / "gououiad-cnie-full.json"

MARKDOWN_MIN_CORE = 0.40
STRUCTURED_MIN_CORE = 0.55

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


@dataclass(frozen=True)
class PathSpec:
    path_id: str
    mode: str  # markdown | structured
    catalog_id: str
    label: str


PATHS: tuple[PathSpec, ...] = (
    PathSpec("repody:vlm:markdown", "markdown", REPODY_VLM_CATALOG_ID, "NuExtract markdown"),
    PathSpec("repody:vlm:structured", "structured", REPODY_VLM_CATALOG_ID, "NuExtract structured"),
    PathSpec("paddleocr:v6", "markdown", PADDLEOCR_V6_CATALOG_ID, "PP-OCRv6 markdown"),
    PathSpec(
        "paddleocr:qwen", "structured", PADDLEOCR_QWEN_CATALOG_ID, "PP-OCRv6 + Qwen structured"
    ),
    PathSpec("glm:ocr", "markdown", GLM_OCR_CATALOG_ID, "GLM-OCR official"),
    PathSpec("glm:qwen", "structured", GLM_OCR_QWEN_CATALOG_ID, "GLM-OCR + Qwen structured"),
    PathSpec("glm:ocr:id-card", "markdown", GLM_OCR_CATALOG_ID, "GLM-OCR ID-card profile"),
)


def _bundle(path: Path) -> DocumentBundle:
    data = path.read_bytes()
    mime = resolve_mime(data=data, declared=None)
    return DocumentBundle(raw_bytes=data, mime_type=mime)


def _ratio(score: dict[str, Any], key: str = "core") -> float:
    got = float(score.get(f"{key}_score") or 0)
    mx = float(score.get(f"{key}_max") or 0) or 1.0
    return got / mx


def _schema_from_side(side: dict[str, Any]) -> list[SchemaFieldSpec]:
    rows: list[SchemaFieldSpec] = []
    for field in (side.get("core_fields") or []) + (side.get("hard_fields") or []):
        field_id = str(field["id"])
        template = "verbatim-string"
        if field_id in {"dob_full", "valid_2035"}:
            template = "date"
        rows.append(
            SchemaFieldSpec(
                name=field_id,
                description=str(field.get("label") or field_id),
                template_type=template,
            )
        )
    return rows


def _fields_map(result_fields: list[Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in result_fields:
        if isinstance(field, dict):
            key = field.get("key") or field.get("name")
            value = field.get("value")
        else:
            key = getattr(field, "key", None) or getattr(field, "name", None)
            value = getattr(field, "value", None)
        if not key:
            continue
        out[str(key)] = "" if value is None else str(value)
    return out


async def _openai_reachable(base_url: str) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/models"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
        return response.status_code < 500, url
    except (httpx.HTTPError, OSError) as exc:
        return False, f"{url} ({exc})"


async def _paddle_reachable(base_url: str) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/ocr"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json={})
        ok = response.status_code < 500 or response.status_code in {400, 422}
        return ok, url
    except (httpx.HTTPError, OSError) as exc:
        return False, f"{url} ({exc})"


async def _glm_reachable(base_url: str) -> tuple[bool, str]:
    raw = base_url.rstrip("/")
    path = (urlparse(raw if "://" in raw else f"http://{raw}").path or "").rstrip("/")
    url = f"{raw}/models" if path.endswith("/v1") else f"{raw}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
        return response.status_code < 500, url
    except (httpx.HTTPError, OSError) as exc:
        return False, f"{url} ({exc})"


async def _run_markdown_pair(
    runner: Callable[[DocumentBundle], Awaitable[Any]],
) -> tuple[str, str, int, int]:
    front = _bundle(FRONT_PATH)
    back = _bundle(BACK_PATH)
    t0 = time.perf_counter()
    front_result = await runner(front)
    front_ms = int((time.perf_counter() - t0) * 1000)
    t1 = time.perf_counter()
    back_result = await runner(back)
    back_ms = int((time.perf_counter() - t1) * 1000)
    return (
        front_result.markdown_text or "",
        back_result.markdown_text or "",
        front_ms,
        back_ms,
    )


async def _run_nuextract_markdown() -> dict[str, Any]:
    async def _one(bundle: DocumentBundle):
        return await extract_with_repody_vlm(
            bundle,
            [],
            "CNIE",
            markdown_extraction=True,
        )

    front_md, back_md, front_ms, back_ms = await _run_markdown_pair(_one)
    score = score_gououiad_cnie_markdown(front_md, back_md, include_hard=True)
    return {
        "front_ms": front_ms,
        "back_ms": back_ms,
        "wall_ms": front_ms + back_ms,
        "front_chars": len(front_md),
        "back_chars": len(back_md),
        "front_preview": front_md[:1200],
        "back_preview": back_md[:1200],
        "score": score,
    }


async def _run_nuextract_structured(expectations: dict[str, Any]) -> dict[str, Any]:
    front_schema = _schema_from_side(expectations["front"])
    back_schema = _schema_from_side(expectations["back"])
    front = _bundle(FRONT_PATH)
    back = _bundle(BACK_PATH)

    t0 = time.perf_counter()
    front_result = await extract_with_repody_vlm(
        front,
        front_schema,
        "CNIE Recto",
        extraction_instructions=FRONT_INSTRUCTIONS,
        markdown_extraction=False,
    )
    front_ms = int((time.perf_counter() - t0) * 1000)
    t1 = time.perf_counter()
    back_result = await extract_with_repody_vlm(
        back,
        back_schema,
        "CNIE Verso",
        extraction_instructions=BACK_INSTRUCTIONS,
        markdown_extraction=False,
    )
    back_ms = int((time.perf_counter() - t1) * 1000)

    front_fields = _fields_map(front_result.fields)
    back_fields = _fields_map(back_result.fields)
    score = score_gououiad_cnie_fields(front_fields, back_fields, include_hard=True)
    return {
        "front_ms": front_ms,
        "back_ms": back_ms,
        "wall_ms": front_ms + back_ms,
        "front_fields": front_fields,
        "back_fields": back_fields,
        "raw_front": front_result.raw_text,
        "raw_back": back_result.raw_text,
        "score": score,
    }


async def _run_paddle_markdown() -> dict[str, Any]:
    async def _one(bundle: DocumentBundle):
        return await extract_with_paddleocr_v6(bundle, [], "CNIE")

    front_md, back_md, front_ms, back_ms = await _run_markdown_pair(_one)
    score = score_gououiad_cnie_markdown(front_md, back_md, include_hard=True)
    return {
        "front_ms": front_ms,
        "back_ms": back_ms,
        "wall_ms": front_ms + back_ms,
        "front_chars": len(front_md),
        "back_chars": len(back_md),
        "front_preview": front_md[:1200],
        "back_preview": back_md[:1200],
        "score": score,
    }


async def _run_glm_markdown(*, id_card_profile: bool) -> dict[str, Any]:
    env_key = "AUDIT_GLM_OCR_ID_CARD_PROFILE"
    previous = os.environ.get(env_key)
    os.environ[env_key] = "true" if id_card_profile else "false"
    get_settings.cache_clear()
    reset_glm_ocr_sdk_client()
    try:

        async def _one(bundle: DocumentBundle):
            return await extract_with_glm_ocr(bundle, [], "CNIE")

        try:
            front_md, back_md, front_ms, back_ms = await _run_markdown_pair(_one)
        except RuntimeError as exc:
            if id_card_profile:
                raise
            return {
                "id_card_profile": id_card_profile,
                "front_ms": 0,
                "back_ms": 0,
                "wall_ms": 0,
                "front_chars": 0,
                "back_chars": 0,
                "front_preview": "",
                "back_preview": "",
                "note": (
                    "Official GLM-OCR profile skips image/chart layout regions; "
                    "CNIE photos land in image regions so markdown is empty without "
                    "AUDIT_GLM_OCR_ID_CARD_PROFILE=true."
                ),
                "error": str(exc),
                "score": score_gououiad_cnie_markdown("", "", include_hard=True),
            }
        score = score_gououiad_cnie_markdown(front_md, back_md, include_hard=True)
        return {
            "id_card_profile": id_card_profile,
            "front_ms": front_ms,
            "back_ms": back_ms,
            "wall_ms": front_ms + back_ms,
            "front_chars": len(front_md),
            "back_chars": len(back_md),
            "front_preview": front_md[:1200],
            "back_preview": back_md[:1200],
            "score": score,
        }
    finally:
        reset_glm_ocr_sdk_client()
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous
        get_settings.cache_clear()


async def _run_paddleocr_qwen_structured(expectations: dict[str, Any]) -> dict[str, Any]:
    front_schema = _schema_from_side(expectations["front"])
    back_schema = _schema_from_side(expectations["back"])
    front = _bundle(FRONT_PATH)
    back = _bundle(BACK_PATH)

    t0 = time.perf_counter()
    front_result = await extract_with_paddleocr_qwen(
        front,
        front_schema,
        "CNIE Recto",
        extraction_instructions=FRONT_INSTRUCTIONS,
    )
    front_ms = int((time.perf_counter() - t0) * 1000)
    t1 = time.perf_counter()
    back_result = await extract_with_paddleocr_qwen(
        back,
        back_schema,
        "CNIE Verso",
        extraction_instructions=BACK_INSTRUCTIONS,
    )
    back_ms = int((time.perf_counter() - t1) * 1000)

    front_fields = _fields_map(front_result.fields)
    back_fields = _fields_map(back_result.fields)
    score = score_gououiad_cnie_fields(front_fields, back_fields, include_hard=True)
    return {
        "front_ms": front_ms,
        "back_ms": back_ms,
        "wall_ms": front_ms + back_ms,
        "front_fields": front_fields,
        "back_fields": back_fields,
        "raw_front": front_result.raw_text,
        "raw_back": back_result.raw_text,
        "score": score,
    }


async def _run_glm_qwen_structured(expectations: dict[str, Any]) -> dict[str, Any]:
    front_schema = _schema_from_side(expectations["front"])
    back_schema = _schema_from_side(expectations["back"])
    front = _bundle(FRONT_PATH)
    back = _bundle(BACK_PATH)
    reset_glm_ocr_sdk_client()
    try:
        t0 = time.perf_counter()
        front_result = await extract_with_glm_ocr_qwen(
            front,
            front_schema,
            "CNIE Recto",
            extraction_instructions=FRONT_INSTRUCTIONS,
        )
        front_ms = int((time.perf_counter() - t0) * 1000)
        t1 = time.perf_counter()
        back_result = await extract_with_glm_ocr_qwen(
            back,
            back_schema,
            "CNIE Verso",
            extraction_instructions=BACK_INSTRUCTIONS,
        )
        back_ms = int((time.perf_counter() - t1) * 1000)
    finally:
        reset_glm_ocr_sdk_client()

    front_fields = _fields_map(front_result.fields)
    back_fields = _fields_map(back_result.fields)
    score = score_gououiad_cnie_fields(front_fields, back_fields, include_hard=True)
    return {
        "front_ms": front_ms,
        "back_ms": back_ms,
        "wall_ms": front_ms + back_ms,
        "front_fields": front_fields,
        "back_fields": back_fields,
        "raw_front": front_result.raw_text,
        "raw_back": back_result.raw_text,
        "score": score,
    }


async def _probe_services() -> dict[str, Any]:
    settings = get_settings()
    nuextract_ok, nuextract_url = await _openai_reachable(settings.llamacpp_base_url)
    glm_ok, glm_url = await _glm_reachable(settings.glm_ocr_base_url)
    paddle_ok, paddle_url = await _paddle_reachable(settings.paddleocr_v6_base_url)
    qwen_ok, qwen_url = await _openai_reachable(settings.qwen35_base_url)
    return {
        "nuextract": {
            "base_url": settings.llamacpp_base_url,
            "probe_url": nuextract_url,
            "reachable": nuextract_ok,
            "enabled": settings.repody_vlm_enabled,
        },
        "glm_ocr": {
            "base_url": settings.glm_ocr_base_url,
            "probe_url": glm_url,
            "reachable": glm_ok,
            "enabled": settings.glm_ocr_enabled,
            "model": settings.glm_ocr_served_model,
        },
        "paddleocr_v6": {
            "base_url": settings.paddleocr_v6_base_url,
            "probe_url": paddle_url,
            "reachable": paddle_ok,
            "enabled": settings.paddleocr_v6_enabled,
        },
        "qwen35": {
            "base_url": settings.qwen35_base_url,
            "probe_url": qwen_url,
            "reachable": qwen_ok,
            "enabled": settings.paddleocr_qwen_enabled,
            "model": settings.qwen35_served_model,
        },
    }


def _evaluate(path: PathSpec, payload: dict[str, Any]) -> dict[str, Any]:
    score = payload.get("score") or {}
    core_ratio = _ratio(score, "core")
    total_ratio = _ratio(score, "total")
    min_core = STRUCTURED_MIN_CORE if path.mode == "structured" else MARKDOWN_MIN_CORE
    expected_limitation = bool(payload.get("note")) and path.path_id == "glm:ocr"
    passed = core_ratio >= min_core
    if path.mode == "markdown":
        passed = (
            passed
            and int(payload.get("front_chars") or 0) > 0
            and int(payload.get("back_chars") or 0) > 0
        )
    if path.mode == "structured":
        passed = passed and bool(score.get("cin_hit"))
    return {
        "passed": passed,
        "expected_limitation": expected_limitation,
        "core_ratio": round(core_ratio, 4),
        "total_ratio": round(total_ratio, 4),
        "min_core_ratio": min_core,
        "cin_hit": score.get("cin_hit"),
        "mrz_hit": score.get("mrz_hit"),
        "primary_hit": score.get("primary_hit"),
        "core": f"{score.get('core_score')}/{score.get('core_max')}",
        "hard": f"{score.get('hard_score')}/{score.get('hard_max')}",
        "total": f"{score.get('total_score')}/{score.get('total_max')}",
    }


def _print_summary(rows: list[dict[str, Any]]) -> None:
    print("\n=== Gououiad CNIE benchmark ===")
    print(
        f"{'path':<22} {'mode':<11} {'wall_ms':>8} {'core':>12} {'ratio':>7} {'cin':>4} {'mrz':>4} {'ok':>6}"
    )
    print("-" * 80)
    for row in rows:
        ev = row.get("evaluation") or {}
        if row.get("skipped"):
            ok = "SKIP"
        elif ev.get("expected_limitation"):
            ok = "LIMIT"
        elif ev.get("passed"):
            ok = "PASS"
        else:
            ok = "FAIL"
        print(
            f"{row.get('path_id', ''):<22} "
            f"{row.get('mode', ''):<11} "
            f"{row.get('wall_ms', '-'):>8} "
            f"{ev.get('core', '-'):>12} "
            f"{ev.get('core_ratio', '-'):>7} "
            f"{'Y' if ev.get('cin_hit') else 'N':>4} "
            f"{'Y' if ev.get('mrz_hit') else 'N':>4} "
            f"{ok:>6}"
        )
    passed = sum(1 for row in rows if (row.get("evaluation") or {}).get("passed"))
    limitations = sum(1 for row in rows if (row.get("evaluation") or {}).get("expected_limitation"))
    skipped = sum(1 for row in rows if row.get("skipped"))
    failed = sum(
        1
        for row in rows
        if not row.get("skipped")
        and not (row.get("evaluation") or {}).get("passed")
        and not (row.get("evaluation") or {}).get("expected_limitation")
    )
    print("-" * 80)
    print(
        f"Passed {passed} · Failed {failed} · Expected limits {limitations} · "
        f"Skipped {skipped} · Total {len(rows)}"
    )


async def run(args: argparse.Namespace) -> int:
    if not FRONT_PATH.is_file() or not BACK_PATH.is_file():
        print(f"Fixtures missing under {FIXTURES}", file=sys.stderr)
        return 2
    expectations = json.loads(EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    os.environ.setdefault("AUDIT_LLAMACPP_BASE_URL", "http://127.0.0.1:8081/v1")
    os.environ.setdefault("AUDIT_GLM_OCR_BASE_URL", "http://127.0.0.1:8083/v1")
    os.environ.setdefault("AUDIT_PADDLEOCR_V6_BASE_URL", "http://127.0.0.1:8868")
    os.environ.setdefault("AUDIT_REPODY_VLM_ENABLED", "true")
    os.environ.setdefault("AUDIT_GLM_OCR_ENABLED", "true")
    os.environ.setdefault("AUDIT_PADDLEOCR_V6_ENABLED", "true")
    os.environ.setdefault("AUDIT_PADDLEOCR_QWEN_ENABLED", "true")
    os.environ.setdefault("AUDIT_GLM_OCR_QWEN_ENABLED", "true")
    os.environ.setdefault("AUDIT_QWEN35_BASE_URL", "http://127.0.0.1:8084/v1")
    os.environ.setdefault("AUDIT_EXTRACTION_CACHE_ENABLED", "false")
    get_settings.cache_clear()

    services = await _probe_services()
    only = {token.strip() for token in (args.only or "").split(",") if token.strip()}
    selected = [
        path for path in PATHS if not only or path.path_id in only or path.catalog_id in only
    ]
    if args.skip_glm_id_card:
        selected = [path for path in selected if path.path_id != "glm:ocr:id-card"]

    rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    for path in selected:
        row: dict[str, Any] = {
            "path_id": path.path_id,
            "catalog_id": path.catalog_id,
            "label": path.label,
            "mode": path.mode,
        }
        # Stays None whenever the branch below marks the row skipped.
        payload: dict[str, Any] | None = None
        try:
            if path.path_id.startswith("repody:vlm"):
                if not services["nuextract"]["reachable"]:
                    row["skipped"] = True
                    row["error"] = f"NuExtract unreachable at {services['nuextract']['probe_url']}"
                elif path.mode == "markdown":
                    payload = await _run_nuextract_markdown()
                else:
                    payload = await _run_nuextract_structured(expectations)
            elif path.path_id == "paddleocr:v6":
                if not services["paddleocr_v6"]["reachable"]:
                    row["skipped"] = True
                    row["error"] = (
                        f"PP-OCRv6 unreachable at {services['paddleocr_v6']['probe_url']}"
                    )
                else:
                    payload = await _run_paddle_markdown()
            elif path.path_id == "paddleocr:qwen":
                if not services["paddleocr_v6"]["reachable"]:
                    row["skipped"] = True
                    row["error"] = (
                        f"PP-OCRv6 unreachable at {services['paddleocr_v6']['probe_url']}"
                    )
                elif not services["qwen35"]["reachable"]:
                    row["skipped"] = True
                    row["error"] = f"Qwen unreachable at {services['qwen35']['probe_url']}"
                else:
                    payload = await _run_paddleocr_qwen_structured(expectations)
            elif path.path_id == "glm:qwen":
                if not services["glm_ocr"]["reachable"]:
                    row["skipped"] = True
                    row["error"] = f"GLM-OCR unreachable at {services['glm_ocr']['probe_url']}"
                elif not services["qwen35"]["reachable"]:
                    row["skipped"] = True
                    row["error"] = f"Qwen unreachable at {services['qwen35']['probe_url']}"
                else:
                    payload = await _run_glm_qwen_structured(expectations)
            elif path.path_id.startswith("glm:ocr"):
                if not services["glm_ocr"]["reachable"]:
                    row["skipped"] = True
                    row["error"] = f"GLM-OCR unreachable at {services['glm_ocr']['probe_url']}"
                else:
                    payload = await _run_glm_markdown(
                        id_card_profile=path.path_id == "glm:ocr:id-card"
                    )
            else:
                row["skipped"] = True
                row["error"] = f"Unknown path {path.path_id}"
                rows.append(row)
                continue

            if payload is not None and not row.get("skipped"):
                row.update(payload)
                row["wall_ms"] = payload.get("wall_ms")
                row["evaluation"] = _evaluate(path, payload)
        except Exception as exc:
            row["error"] = repr(exc)
            row["evaluation"] = {"passed": False, "core_ratio": 0.0}

        rows.append(row)
        ev = row.get("evaluation") or {}
        status = (
            "SKIP"
            if row.get("skipped")
            else (
                "LIMIT"
                if ev.get("expected_limitation")
                else ("PASS" if ev.get("passed") else "FAIL")
            )
        )
        print(
            f"[{status}] {path.label} ({path.path_id}) — {ev.get('core', '-')} in {row.get('wall_ms', '-')}ms"
        )

    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC).isoformat(),
        "fixture_id": expectations.get("fixture_id"),
        "fixtures": {
            "front": str(FRONT_PATH),
            "back": str(BACK_PATH),
            "expectations": str(EXPECTATIONS_PATH),
        },
        "services": services,
        "settings": {
            "markdown_min_core_ratio": MARKDOWN_MIN_CORE,
            "structured_min_core_ratio": STRUCTURED_MIN_CORE,
            "skip_glm_id_card": args.skip_glm_id_card,
            "only": sorted(only) if only else None,
        },
        "wall_ms_total": int((time.perf_counter() - started) * 1000),
        "paths": rows,
        "summary": {
            "passed": sum(1 for row in rows if (row.get("evaluation") or {}).get("passed")),
            "failed": sum(
                1
                for row in rows
                if not row.get("skipped")
                and not (row.get("evaluation") or {}).get("passed")
                and not (row.get("evaluation") or {}).get("expected_limitation")
            ),
            "expected_limitations": sum(
                1 for row in rows if (row.get("evaluation") or {}).get("expected_limitation")
            ),
            "skipped": sum(1 for row in rows if row.get("skipped")),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _print_summary(rows)
    print(f"\nReport: {args.output}")
    return 0 if report["summary"]["failed"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark all Gououiad CNIE extraction paths.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"JSON report path (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated path ids or catalog ids to run (default: all)",
    )
    parser.add_argument(
        "--skip-glm-id-card",
        action="store_true",
        help="Skip glm:ocr:id-card profile run",
    )
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
