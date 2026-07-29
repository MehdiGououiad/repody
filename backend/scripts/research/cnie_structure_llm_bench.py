#!/usr/bin/env python3
"""Gououiad CNIE experiment: compare JSON fields from OCR+LLM vs Structure+LLM.

Primary goal: same CNIE schema JSON from two text sources, scored side-by-side.

Arms:
  ocr          — PP-OCRv6 front+back text (markdown score only)
  structure    — PP-StructureV3 front+back markdown (markdown score only)
  json-compare — Qwen3.5-4B text→JSON on both OCR and Structure texts;
                 writes side-by-side field JSON + field scores
  ocr-llm      — one-shot OCR + LLM (needs OCR + Qwen up together)
  vlm          — NuExtract3 vision baseline (optional)

Sequential host flow (recommended — do not run Paddle + Qwen in parallel):
  1) start OCR → --arm ocr → stop OCR
  2) start Structure → --arm structure --no-structure-llm → stop Structure
  3) start Qwen → --arm json-compare --from-dir <same out dir>

Reports: benchmark-reports/cnie-structure-llm/
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from repody.benchmarking.ocr import (
    load_expectations,
    score_gououiad_cnie_fields,
    score_gououiad_cnie_markdown,
)
from repody.extraction.paddleocr_v6 import (
    file_type_for_mime,
    markdown_from_ocr_result,
    paddle_error_message,
)
from repody.extraction.types import SchemaFieldSpec, load_document_bundle
from repody.extraction.vlm import (
    extract_with_repody_vlm,
    extract_with_repody_vlm_cloud,
)
from repody.infra.storage.mime import sniff_mime

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "e2e" / "fixtures" / "documents"
EXPECTATIONS_PATH = FIXTURES / "gououiad-cnie.ocr-expectations.json"
FRONT_PATH = FIXTURES / "gououiad-cnie-front.png"
BACK_PATH = FIXTURES / "gououiad-cnie-back.png"
REPORT_DIR = ROOT / "benchmark-reports" / "cnie-structure-llm"

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _env(name: str, default: str = "") -> str:
    import os

    return (os.environ.get(name) or default).strip()


def _load_side(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    mime = sniff_mime(data) or "image/jpeg"
    return data, mime


def _schema_from_side(side: dict[str, Any]) -> list[SchemaFieldSpec]:
    fields: list[SchemaFieldSpec] = []
    for row in (side.get("core_fields") or []) + (side.get("hard_fields") or []):
        fields.append(
            SchemaFieldSpec(
                name=str(row["id"]),
                description=str(row.get("label") or row["id"]),
            )
        )
    return fields


# Fair prompts: clear what to extract, no expected values, no answer examples.
_FAIR_PROMPTS_FRONT: dict[str, str] = {
    "national_id": "National identity number (N° / CIN) printed on the front of the card.",
    "first_name": "Given name (prénom) in Latin script.",
    "last_name": "Family name (nom) in Latin script.",
    "dob_1998": "Four-digit birth year only.",
    "dob_full": "Full date of birth as printed on the card.",
    "valid_2035": "Card expiry / valid-until date as printed.",
    "can_serial": "CAN serial number digits printed on the card.",
    "birth_place": "Place of birth as printed.",
    "document_title": "Official document title line in French.",
    "kingdom_header": "Kingdom / country header line in French.",
    "arabic_first": "Given name written in Arabic script.",
}

_FAIR_PROMPTS_BACK: dict[str, str] = {
    "national_id": "National identity number (CIN) printed on the back of the card.",
    "father_name": "Father's name as printed after Fils de / equivalent.",
    "mother_name": "Mother's name as printed after Et de / equivalent.",
    "address_city": "City from the address block.",
    "address_street": "Street name from the address block.",
    "gender": "Sex / gender code as printed.",
    "mrz_line1_prefix": "Machine-readable zone line 1 text (leading characters).",
    "mrz_line2_dob": "Date-of-birth encoding from MRZ line 2.",
    "mrz_line2_expiry": "Expiry encoding from MRZ line 2.",
    "mrz_line3_name": "Name line from the MRZ (surname and given name).",
    "opi_code": "Internal OPI code printed on the back.",
    "etat_civil": "État civil registry number digits.",
    "address_number": "Street number from the address block.",
}

_CLOUD_DOC_INSTRUCTIONS = (
    "Extract the template fields from this Moroccan national identity card image. "
    "Use only values visible on the document. "
    "If a field is missing or unreadable, leave it empty. "
    "Do not invent or guess values."
)


def _fair_schema_from_side(side: str, expectations: dict[str, Any]) -> list[SchemaFieldSpec]:
    prompts = _FAIR_PROMPTS_FRONT if side == "front" else _FAIR_PROMPTS_BACK
    side_spec = expectations[side]
    fields: list[SchemaFieldSpec] = []
    for row in (side_spec.get("core_fields") or []) + (side_spec.get("hard_fields") or []):
        field_id = str(row["id"])
        fields.append(
            SchemaFieldSpec(
                name=field_id,
                description=prompts.get(field_id) or str(row.get("label") or field_id),
            )
        )
    return fields


def _fields_to_dict(extracted: list[Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in extracted:
        key = getattr(item, "key", None) or getattr(item, "name", None)
        if not key:
            continue
        value = getattr(item, "value", "") or ""
        out[str(key)] = str(value)
    return out


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    fence = _JSON_FENCE.search(text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _flatten_fields(data: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            nested = value.get("value", value)
            out[str(key)] = "" if nested is None else str(nested)
        elif value is None:
            out[str(key)] = ""
        else:
            out[str(key)] = str(value)
    return out


def _score_summary(score: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_score": score.get("total_score"),
        "total_max": score.get("total_max"),
        "core_score": score.get("core_score"),
        "core_max": score.get("core_max"),
        "hard_score": score.get("hard_score"),
        "hard_max": score.get("hard_max"),
        "cin_hit": score.get("cin_hit"),
        "mrz_hit": score.get("mrz_hit"),
        "primary_hit": score.get("primary_hit"),
        "hits": score.get("hits"),
    }


async def _post_ocr_v6(client: httpx.AsyncClient, data: bytes, mime: str, base: str) -> str:
    payload = {
        "file": base64.b64encode(data).decode("ascii"),
        "fileType": file_type_for_mime(mime),
        "visualize": False,
    }
    response = await client.post(f"{base.rstrip('/')}/ocr", json=payload)
    response.raise_for_status()
    body = response.json()
    err = paddle_error_message(body, label="PP-OCRv6")
    if err:
        raise RuntimeError(err)
    return markdown_from_ocr_result(body)


def _texts_from_pruned(pruned: dict[str, Any]) -> str:
    chunks: list[str] = []
    parsing = pruned.get("parsing_res_list") or pruned.get("parsingResList") or []
    if isinstance(parsing, list):
        for block in parsing:
            if not isinstance(block, dict):
                continue
            content = block.get("block_content") or block.get("blockContent") or ""
            if isinstance(content, str) and content.strip():
                chunks.append(content.strip())
    ocr = pruned.get("overall_ocr_res") or pruned.get("overallOcrRes") or {}
    if isinstance(ocr, dict):
        rec = ocr.get("rec_texts") or ocr.get("recTexts") or []
        if isinstance(rec, list):
            lines = [t.strip() for t in rec if isinstance(t, str) and t.strip()]
            if lines:
                chunks.append("\n".join(lines))
    return "\n\n".join(chunks).strip()


def _markdown_from_layout_payload(payload: dict[str, Any]) -> str:
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        result = payload if isinstance(payload, dict) else {}
    pages = (
        result.get("layoutParsingResults")
        or result.get("layout_parsing_results")
        or []
    )
    if not isinstance(pages, list):
        return ""
    chunks: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        md = page.get("markdown") or page.get("Markdown") or {}
        md_text = ""
        if isinstance(md, dict):
            text = md.get("text") or md.get("Text") or ""
            if isinstance(text, str):
                md_text = text.strip()
        elif isinstance(md, str):
            md_text = md.strip()
        # CNIE photos often become image-only markdown; fall back to pruned OCR text.
        looks_like_img_only = (
            not md_text
            or md_text.lstrip().startswith("<div")
            or ("<img " in md_text and len(md_text) < 400)
        )
        pruned = page.get("prunedResult") or page.get("pruned_result") or {}
        pruned_text = _texts_from_pruned(pruned) if isinstance(pruned, dict) else ""
        if looks_like_img_only and pruned_text:
            chunks.append(pruned_text)
        elif md_text:
            chunks.append(md_text)
        elif pruned_text:
            chunks.append(pruned_text)
    return "\n\n".join(chunks).strip()


async def _post_structure_http(
    client: httpx.AsyncClient,
    data: bytes,
    mime: str,
    base: str,
) -> str:
    payload = {
        "file": base64.b64encode(data).decode("ascii"),
        "fileType": file_type_for_mime(mime),
        "visualize": False,
        # CNIE is not a formula/table doc — keep layout OCR text cleaner.
        "useFormulaRecognition": False,
        "useTableRecognition": False,
        "useChartRecognition": False,
        "useSealRecognition": False,
    }
    response = await client.post(f"{base.rstrip('/')}/layout-parsing", json=payload)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("PP-StructureV3 returned a non-object JSON body.")
    err = paddle_error_message(body, label="PP-StructureV3")
    if err:
        raise RuntimeError(err)
    text = _markdown_from_layout_payload(body)
    if not text.strip():
        raise RuntimeError("PP-StructureV3 /layout-parsing returned empty markdown.")
    return text


def _structure_inprocess(path: Path, out_dir: Path) -> str:
    """Official in-process PP-StructureV3 via paddlex.create_pipeline."""
    from paddlex import create_pipeline  # type: ignore[import-untyped]

    pipeline = create_pipeline(pipeline="PP-StructureV3")
    chunks: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for res in pipeline.predict(input=str(path)):
        md = getattr(res, "markdown", None)
        if isinstance(md, dict):
            text = md.get("text") or md.get("markdown") or ""
            if text:
                chunks.append(str(text).strip())
        elif isinstance(md, str) and md.strip():
            chunks.append(md.strip())
        else:
            # Fallback: some builds expose markdown as attribute / method result.
            maybe = getattr(res, "str", None)
            if callable(maybe):
                chunks.append(str(maybe()).strip())
        try:
            res.save_to_markdown(save_path=str(out_dir))
        except Exception:
            pass
        try:
            res.save_to_json(save_path=str(out_dir))
        except Exception:
            pass
    text = "\n\n".join(c for c in chunks if c).strip()
    if not text:
        # Last resort: gather any .md written by save_to_markdown
        md_files = sorted(out_dir.glob("*.md"))
        text = "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in md_files).strip()
    if not text:
        raise RuntimeError("PP-StructureV3 in-process predict returned empty markdown.")
    return text


async def _qwen_text_to_json(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    model: str,
    schema: list[SchemaFieldSpec],
    ocr_text: str,
    side: str,
) -> tuple[dict[str, str], str]:
    keys = ", ".join(f'"{f.name}"' for f in schema)
    field_lines = "\n".join(f'- "{f.name}": {f.description}' for f in schema)
    # Qwen3.5 often spends the whole budget on thinking; disable it.
    system = (
        "/no_think\n"
        "Extract identity-document fields from OCR text. "
        "Reply with one flat JSON object only. No markdown fences. No commentary. "
        f"Keys must be exactly: {keys}. "
        "Use empty string when unknown. Copy values from the text; do not invent."
    )
    user = (
        f"Side: {side} of a Moroccan CNIE.\n"
        f"Schema:\n{field_lines}\n\n"
        f"Text:\n{ocr_text}\n\n"
        "JSON:"
    )
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 768,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    response = await client.post(
        f"{base_url.rstrip('/')}/chat/completions",
        json=payload,
    )
    response.raise_for_status()
    body = response.json()
    raw = str(body["choices"][0]["message"]["content"])
    # Strip optional thinking blocks if the server ignored /no_think.
    raw_clean = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()
    parsed = _parse_json_object(raw_clean)
    flat = _flatten_fields(parsed)
    # Flat object projection (NuExtract fields_from_nuextract_json).
    fields = {f.name: str(flat.get(f.name, "") or "").strip() for f in schema}
    return fields, raw


async def run_vlm_arm(
    front_bytes: bytes,
    front_mime: str,
    back_bytes: bytes,
    back_mime: str,
    expectations: dict[str, Any],
) -> dict[str, Any]:
    front_schema = _schema_from_side(expectations["front"])
    back_schema = _schema_from_side(expectations["back"])
    front_bundle = load_document_bundle(front_bytes, front_mime)
    back_bundle = load_document_bundle(back_bytes, back_mime)

    started = time.perf_counter()
    front_result = await extract_with_repody_vlm(
        front_bundle, front_schema, "cnie_front"
    )
    front_ms = int((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    back_result = await extract_with_repody_vlm(
        back_bundle, back_schema, "cnie_back"
    )
    back_ms = int((time.perf_counter() - started) * 1000)

    front_fields = _fields_to_dict(front_result.fields)
    back_fields = _fields_to_dict(back_result.fields)
    score = score_gououiad_cnie_fields(front_fields, back_fields)
    return {
        "arm": "vlm",
        "elapsed_ms": {"front": front_ms, "back": back_ms, "total": front_ms + back_ms},
        "front_fields": front_fields,
        "back_fields": back_fields,
        "score": _score_summary(score),
        "score_kind": "fields",
    }


async def run_vlm_cloud_arm(
    front_bytes: bytes,
    front_mime: str,
    back_bytes: bytes,
    back_mime: str,
    expectations: dict[str, Any],
) -> dict[str, Any]:
    """NuExtract Cloud vision→JSON with fair field prompts (no answer hints)."""
    front_schema = _fair_schema_from_side("front", expectations)
    back_schema = _fair_schema_from_side("back", expectations)
    front_bundle = load_document_bundle(front_bytes, front_mime)
    back_bundle = load_document_bundle(back_bytes, back_mime)

    started = time.perf_counter()
    front_result = await extract_with_repody_vlm_cloud(
        front_bundle,
        front_schema,
        "cnie_front",
        extraction_instructions=_CLOUD_DOC_INSTRUCTIONS,
    )
    front_ms = int((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    back_result = await extract_with_repody_vlm_cloud(
        back_bundle,
        back_schema,
        "cnie_back",
        extraction_instructions=_CLOUD_DOC_INSTRUCTIONS,
    )
    back_ms = int((time.perf_counter() - started) * 1000)

    front_fields = _fields_to_dict(front_result.fields)
    back_fields = _fields_to_dict(back_result.fields)
    # Normalize NuExtract "—" empties for scoring
    front_fields = {
        k: ("" if v in {"—", "-", "null", "None"} else v) for k, v in front_fields.items()
    }
    back_fields = {
        k: ("" if v in {"—", "-", "null", "None"} else v) for k, v in back_fields.items()
    }
    score = score_gououiad_cnie_fields(front_fields, back_fields)
    return {
        "arm": "vlm-cloud",
        "elapsed_ms": {"front": front_ms, "back": back_ms, "total": front_ms + back_ms},
        "front_fields": front_fields,
        "back_fields": back_fields,
        "front_prompts": {f.name: f.description for f in front_schema},
        "back_prompts": {f.name: f.description for f in back_schema},
        "document_instructions": _CLOUD_DOC_INSTRUCTIONS,
        "score": _score_summary(score),
        "score_kind": "fields",
    }


async def run_ocr_arm(
    client: httpx.AsyncClient,
    front_bytes: bytes,
    front_mime: str,
    back_bytes: bytes,
    back_mime: str,
    ocr_base: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    front_md = await _post_ocr_v6(client, front_bytes, front_mime, ocr_base)
    front_ms = int((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    back_md = await _post_ocr_v6(client, back_bytes, back_mime, ocr_base)
    back_ms = int((time.perf_counter() - started) * 1000)

    score = score_gououiad_cnie_markdown(front_md, back_md)
    return {
        "arm": "ocr",
        "elapsed_ms": {"front": front_ms, "back": back_ms, "total": front_ms + back_ms},
        "front_markdown": front_md,
        "back_markdown": back_md,
        "score": _score_summary(score),
        "score_kind": "markdown",
    }


async def run_llm_on_texts(
    client: httpx.AsyncClient,
    *,
    expectations: dict[str, Any],
    front_md: str,
    back_md: str,
    qwen_base: str,
    qwen_model: str,
    arm_name: str = "llm",
    ocr_elapsed: dict[str, Any] | None = None,
    ocr_markdown_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Qwen text→JSON only — no OCR/Structure process required."""
    front_schema = _schema_from_side(expectations["front"])
    back_schema = _schema_from_side(expectations["back"])

    started = time.perf_counter()
    front_fields, front_raw = await _qwen_text_to_json(
        client,
        base_url=qwen_base,
        model=qwen_model,
        schema=front_schema,
        ocr_text=front_md,
        side="front",
    )
    front_ms = int((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    back_fields, back_raw = await _qwen_text_to_json(
        client,
        base_url=qwen_base,
        model=qwen_model,
        schema=back_schema,
        ocr_text=back_md,
        side="back",
    )
    back_ms = int((time.perf_counter() - started) * 1000)

    score = score_gououiad_cnie_fields(front_fields, back_fields)
    result: dict[str, Any] = {
        "arm": arm_name,
        "elapsed_ms": {
            "llm_front": front_ms,
            "llm_back": back_ms,
            "total": front_ms + back_ms,
        },
        "front_markdown": front_md,
        "back_markdown": back_md,
        "front_fields": front_fields,
        "back_fields": back_fields,
        "front_llm_raw": front_raw[:4000],
        "back_llm_raw": back_raw[:4000],
        "score": _score_summary(score),
        "score_kind": "fields",
    }
    if ocr_elapsed is not None:
        result["elapsed_ms"]["ocr"] = ocr_elapsed
        result["elapsed_ms"]["total"] = int(ocr_elapsed.get("total") or 0) + front_ms + back_ms
    if ocr_markdown_score is not None:
        result["ocr_markdown_score"] = ocr_markdown_score
    return result


async def run_ocr_llm_arm(
    client: httpx.AsyncClient,
    *,
    front_bytes: bytes,
    front_mime: str,
    back_bytes: bytes,
    back_mime: str,
    expectations: dict[str, Any],
    ocr_base: str,
    qwen_base: str,
    qwen_model: str,
) -> dict[str, Any]:
    ocr = await run_ocr_arm(
        client, front_bytes, front_mime, back_bytes, back_mime, ocr_base
    )
    result = await run_llm_on_texts(
        client,
        expectations=expectations,
        front_md=ocr["front_markdown"],
        back_md=ocr["back_markdown"],
        qwen_base=qwen_base,
        qwen_model=qwen_model,
        arm_name="ocr-llm",
        ocr_elapsed=ocr["elapsed_ms"],
        ocr_markdown_score=ocr["score"],
    )
    return result


def _find_arm_result(results: list[dict[str, Any]], arm_name: str) -> dict[str, Any]:
    for arm in results:
        if arm.get("arm") == arm_name and not arm.get("error"):
            return arm
    raise RuntimeError(f"Missing successful '{arm_name}' result (need prior --arm run).")


def _load_markdown_from_arm(arm: dict[str, Any]) -> tuple[str, str]:
    front = arm.get("front_markdown")
    back = arm.get("back_markdown")
    if not isinstance(front, str) or not isinstance(back, str):
        raise RuntimeError(f"Arm {arm.get('arm')!r} has no front/back markdown.")
    return front, back


def _merge_report(path: Path, new_results: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "fixture_id": None,
            "arms_requested": [],
            "notes": [],
            "results": [],
        }
    by_arm: dict[str, dict[str, Any]] = {}
    for arm in payload.get("results") or []:
        name = str(arm.get("arm") or "")
        if name:
            by_arm[name] = arm
    for arm in new_results:
        name = str(arm.get("arm") or "")
        if name:
            by_arm[name] = arm
    payload["results"] = list(by_arm.values())
    payload["generated_at"] = datetime.now(UTC).isoformat()
    for key, value in extra.items():
        if value is not None:
            payload[key] = value
    requested = list(payload.get("arms_requested") or [])
    for arm in new_results:
        name = str(arm.get("arm") or "")
        if name and name not in requested:
            requested.append(name)
    payload["arms_requested"] = requested
    return payload


def _side_by_side_json(
    ocr_front: dict[str, str],
    ocr_back: dict[str, str],
    structure_front: dict[str, str],
    structure_back: dict[str, str],
) -> dict[str, Any]:
    front_keys = sorted(set(ocr_front) | set(structure_front))
    back_keys = sorted(set(ocr_back) | set(structure_back))
    front_rows = [
        {
            "field": key,
            "ocr_llm": ocr_front.get(key, ""),
            "structure_llm": structure_front.get(key, ""),
            "match": (ocr_front.get(key, "") or "") == (structure_front.get(key, "") or ""),
        }
        for key in front_keys
    ]
    back_rows = [
        {
            "field": key,
            "ocr_llm": ocr_back.get(key, ""),
            "structure_llm": structure_back.get(key, ""),
            "match": (ocr_back.get(key, "") or "") == (structure_back.get(key, "") or ""),
        }
        for key in back_keys
    ]
    return {
        "front": front_rows,
        "back": back_rows,
        "front_match_count": sum(1 for r in front_rows if r["match"]),
        "front_field_count": len(front_rows),
        "back_match_count": sum(1 for r in back_rows if r["match"]),
        "back_field_count": len(back_rows),
    }


async def run_json_compare_arm(
    client: httpx.AsyncClient,
    *,
    expectations: dict[str, Any],
    from_dir: Path,
    qwen_base: str,
    qwen_model: str,
) -> dict[str, Any]:
    """Run Qwen on OCR text and Structure text; compare resulting JSON fields."""
    report_path = from_dir / "report.json"
    if not report_path.exists():
        raise RuntimeError(f"Need prior OCR+Structure report at {report_path}")
    existing = json.loads(report_path.read_text(encoding="utf-8"))
    results = existing.get("results") or []
    ocr_arm = _find_arm_result(results, "ocr")
    structure_arm = _find_arm_result(results, "structure")
    ocr_front_md, ocr_back_md = _load_markdown_from_arm(ocr_arm)
    struct_front_md, struct_back_md = _load_markdown_from_arm(structure_arm)

    ocr_llm = await run_llm_on_texts(
        client,
        expectations=expectations,
        front_md=ocr_front_md,
        back_md=ocr_back_md,
        qwen_base=qwen_base,
        qwen_model=qwen_model,
        arm_name="ocr-llm",
        ocr_elapsed=ocr_arm.get("elapsed_ms"),
        ocr_markdown_score=ocr_arm.get("score"),
    )
    structure_llm = await run_llm_on_texts(
        client,
        expectations=expectations,
        front_md=struct_front_md,
        back_md=struct_back_md,
        qwen_base=qwen_base,
        qwen_model=qwen_model,
        arm_name="structure-llm",
        ocr_elapsed=structure_arm.get("elapsed_ms"),
        ocr_markdown_score=structure_arm.get("score"),
    )
    comparison = _side_by_side_json(
        ocr_llm["front_fields"],
        ocr_llm["back_fields"],
        structure_llm["front_fields"],
        structure_llm["back_fields"],
    )
    return {
        "arm": "json-compare",
        "score_kind": "fields",
        "ocr_llm": ocr_llm,
        "structure_llm": structure_llm,
        "json_comparison": comparison,
        "score": {
            "ocr_llm": ocr_llm["score"],
            "structure_llm": structure_llm["score"],
        },
        "elapsed_ms": {
            "ocr_llm": ocr_llm["elapsed_ms"],
            "structure_llm": structure_llm["elapsed_ms"],
            "total": int(ocr_llm["elapsed_ms"]["total"])
            + int(structure_llm["elapsed_ms"]["total"]),
        },
    }


async def run_structure_arm(
    client: httpx.AsyncClient,
    *,
    front_bytes: bytes,
    front_mime: str,
    back_bytes: bytes,
    back_mime: str,
    front_path: Path,
    back_path: Path,
    expectations: dict[str, Any],
    structure_base: str,
    structure_mode: str,
    artifacts_dir: Path,
    qwen_base: str | None,
    qwen_model: str | None,
) -> dict[str, Any]:
    mode = structure_mode
    if mode == "auto":
        mode = "http" if structure_base else "inprocess"

    started = time.perf_counter()
    if mode == "http":
        front_md = await _post_structure_http(
            client, front_bytes, front_mime, structure_base
        )
    else:
        front_md = await asyncio.to_thread(
            _structure_inprocess, front_path, artifacts_dir / "front"
        )
    front_ms = int((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    if mode == "http":
        back_md = await _post_structure_http(
            client, back_bytes, back_mime, structure_base
        )
    else:
        back_md = await asyncio.to_thread(
            _structure_inprocess, back_path, artifacts_dir / "back"
        )
    back_ms = int((time.perf_counter() - started) * 1000)

    md_score = score_gououiad_cnie_markdown(front_md, back_md)
    _ = qwen_base
    _ = qwen_model
    return {
        "arm": "structure",
        "structure_mode": mode,
        "elapsed_ms": {"front": front_ms, "back": back_ms, "total": front_ms + back_ms},
        "front_markdown": front_md,
        "back_markdown": back_md,
        "score": _score_summary(md_score),
        "score_kind": "markdown",
    }


def _render_markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# CNIE JSON compare: OCR+LLM vs Structure+LLM",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Fixture: `{payload['fixture_id']}`",
        f"- Arms: {', '.join(payload['arms_requested'])}",
        "",
        "## Scores",
        "",
        "| Arm | Kind | Total | Core | Hard | CIN | MRZ | ms |",
        "|---|---|---:|---:|---:|---|---|---:|",
    ]

    def _row(name: str, kind: str, score: dict[str, Any], ms: Any) -> None:
        total = f"{score.get('total_score')}/{score.get('total_max')}"
        core = f"{score.get('core_score')}/{score.get('core_max')}"
        hard = f"{score.get('hard_score')}/{score.get('hard_max')}"
        lines.append(
            f"| {name} | {kind} | {total} | {core} | {hard} | "
            f"{score.get('cin_hit')} | {score.get('mrz_hit')} | {ms} |"
        )

    for arm in payload.get("results") or []:
        if arm.get("error"):
            lines.append(f"| {arm.get('arm')} | error | — | — | — | — | — | — |")
            continue
        if arm.get("arm") == "json-compare":
            ocr_llm = arm.get("ocr_llm") or {}
            structure_llm = arm.get("structure_llm") or {}
            if ocr_llm.get("score"):
                _row(
                    "ocr-llm (JSON)",
                    "fields",
                    ocr_llm["score"],
                    (ocr_llm.get("elapsed_ms") or {}).get("total", "—"),
                )
            if structure_llm.get("score"):
                _row(
                    "structure-llm (JSON)",
                    "fields",
                    structure_llm["score"],
                    (structure_llm.get("elapsed_ms") or {}).get("total", "—"),
                )
            continue
        score = arm.get("score") or {}
        if isinstance(score.get("ocr_llm"), dict):
            continue
        _row(
            str(arm.get("arm")),
            str(arm.get("score_kind") or ""),
            score,
            (arm.get("elapsed_ms") or {}).get("total", "—"),
        )
        llm = arm.get("llm")
        if isinstance(llm, dict) and llm.get("score"):
            _row(
                f"{arm.get('arm')}+llm",
                "fields",
                llm["score"],
                (llm.get("elapsed_ms") or {}).get("total", "—"),
            )

    compare = None
    for arm in payload.get("results") or []:
        if arm.get("arm") == "json-compare":
            compare = arm.get("json_comparison")
            break
    if isinstance(compare, dict):
        lines.extend(
            [
                "",
                "## JSON field side-by-side",
                "",
                f"- Front exact matches: "
                f"`{compare.get('front_match_count')}/{compare.get('front_field_count')}`",
                f"- Back exact matches: "
                f"`{compare.get('back_match_count')}/{compare.get('back_field_count')}`",
                "",
                "### Front",
                "",
                "| Field | OCR+LLM | Structure+LLM | Match |",
                "|---|---|---|---|",
            ]
        )
        for row in compare.get("front") or []:
            lines.append(
                f"| `{row['field']}` | {row['ocr_llm']!s} | {row['structure_llm']!s} | "
                f"{'yes' if row['match'] else 'no'} |"
            )
        lines.extend(
            [
                "",
                "### Back",
                "",
                "| Field | OCR+LLM | Structure+LLM | Match |",
                "|---|---|---|---|",
            ]
        )
        for row in compare.get("back") or []:
            lines.append(
                f"| `{row['field']}` | {row['ocr_llm']!s} | {row['structure_llm']!s} | "
                f"{'yes' if row['match'] else 'no'} |"
            )

    lines.extend(["", "## Notes", ""])
    for note in payload.get("notes") or []:
        lines.append(f"- {note}")
    for arm in payload.get("results") or []:
        if arm.get("error"):
            lines.append(f"- `{arm.get('arm')}` failed: `{arm['error']}`")
    lines.append("")
    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> int:
    expectations = load_expectations(EXPECTATIONS_PATH)
    front_bytes, front_mime = _load_side(FRONT_PATH)
    back_bytes, back_mime = _load_side(BACK_PATH)

    ocr_base = args.ocr_base or _env(
        "AUDIT_PADDLEOCR_V6_BASE_URL", "http://127.0.0.1:8868"
    )
    structure_base = args.structure_base or _env(
        "AUDIT_PADDLE_STRUCTURE_V3_BASE_URL", "http://127.0.0.1:8870"
    )
    qwen_base = args.qwen_base or _env(
        "AUDIT_QWEN35_BASE_URL", "http://127.0.0.1:8084/v1"
    )
    qwen_model = args.qwen_model or _env("AUDIT_QWEN35_MODEL", "Qwen3.5-4B")

    arms = [args.arm]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.output_dir) if args.output_dir else REPORT_DIR / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    from_dir = Path(args.from_dir) if args.from_dir else out_dir

    notes = [
        "JSON compare: same Qwen3.5-4B prompt on OCR text vs Structure markdown.",
        "Structure arm uses official PP-StructureV3 POST /layout-parsing (or in-process).",
        f"Front MIME sniffed as {front_mime}; back as {back_mime}.",
    ]
    results: list[dict[str, Any]] = []
    timeout = httpx.Timeout(600.0, connect=30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for arm in arms:
            print(f"==> arm={arm}")
            try:
                if arm == "vlm":
                    result = await run_vlm_arm(
                        front_bytes,
                        front_mime,
                        back_bytes,
                        back_mime,
                        expectations,
                    )
                elif arm == "vlm-cloud":
                    result = await run_vlm_cloud_arm(
                        front_bytes,
                        front_mime,
                        back_bytes,
                        back_mime,
                        expectations,
                    )
                elif arm == "ocr":
                    result = await run_ocr_arm(
                        client,
                        front_bytes,
                        front_mime,
                        back_bytes,
                        back_mime,
                        ocr_base,
                    )
                elif arm == "ocr-llm":
                    result = await run_ocr_llm_arm(
                        client,
                        front_bytes=front_bytes,
                        front_mime=front_mime,
                        back_bytes=back_bytes,
                        back_mime=back_mime,
                        expectations=expectations,
                        ocr_base=ocr_base,
                        qwen_base=qwen_base,
                        qwen_model=qwen_model,
                    )
                elif arm == "structure":
                    result = await run_structure_arm(
                        client,
                        front_bytes=front_bytes,
                        front_mime=front_mime,
                        back_bytes=back_bytes,
                        back_mime=back_mime,
                        front_path=FRONT_PATH,
                        back_path=BACK_PATH,
                        expectations=expectations,
                        structure_base=structure_base,
                        structure_mode=args.structure_mode,
                        artifacts_dir=out_dir / "structure-artifacts",
                        qwen_base=None,
                        qwen_model=None,
                    )
                elif arm == "json-compare":
                    result = await run_json_compare_arm(
                        client,
                        expectations=expectations,
                        from_dir=from_dir,
                        qwen_base=qwen_base,
                        qwen_model=qwen_model,
                    )
                    # Also persist nested arm scores as top-level siblings for clarity
                    results.append(result["ocr_llm"])
                    results.append(result["structure_llm"])
                else:
                    raise ValueError(f"Unknown arm: {arm}")
                results.append(result)
                if arm == "json-compare":
                    ocr_s = result["ocr_llm"]["score"]
                    st_s = result["structure_llm"]["score"]
                    print(
                        f"    ocr-llm JSON: {ocr_s.get('total_score')}/{ocr_s.get('total_max')}"
                    )
                    print(
                        f"    structure-llm JSON: {st_s.get('total_score')}/{st_s.get('total_max')}"
                    )
                else:
                    score = result.get("score") or {}
                    print(
                        f"    {arm}: {score.get('total_score')}/{score.get('total_max')} "
                        f"({result.get('score_kind')}) in "
                        f"{result.get('elapsed_ms', {}).get('total')}ms"
                    )
            except Exception as exc:
                print(f"    {arm} FAILED: {exc}")
                results.append({"arm": arm, "error": repr(exc)})

    payload = _merge_report(
        out_dir / "report.json",
        results,
        fixture_id=expectations.get("fixture_id"),
        notes=notes,
        endpoints={
            "ocr": ocr_base,
            "structure": structure_base,
            "qwen": qwen_base,
            "qwen_model": qwen_model,
        },
    )
    # Prefer this run's out_dir even when --from-dir pointed elsewhere for inputs
    json_path = out_dir / "report.json"
    md_path = out_dir / "report.md"
    # Also dump raw JSON field objects for easy diffing
    for arm in results:
        if arm.get("arm") in {"ocr-llm", "structure-llm", "vlm", "vlm-cloud"} and arm.get(
            "front_fields"
        ):
            side_path = out_dir / f"{arm['arm']}.fields.json"
            payload_side: dict[str, Any] = {
                "front": arm.get("front_fields"),
                "back": arm.get("back_fields"),
                "score": arm.get("score"),
            }
            if arm.get("front_prompts"):
                payload_side["front_prompts"] = arm.get("front_prompts")
                payload_side["back_prompts"] = arm.get("back_prompts")
                payload_side["document_instructions"] = arm.get("document_instructions")
            side_path.write_text(
                json.dumps(payload_side, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Wrote {side_path}")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_render_markdown_report(payload), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    failed = [r for r in results if r.get("error")]
    return 1 if failed and args.fail_on_error else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--arm",
        choices=["vlm", "vlm-cloud", "ocr", "ocr-llm", "structure", "json-compare"],
        default="json-compare",
        help="Run one arm. Use sequential host orchestration for OCR → Structure → json-compare.",
    )
    p.add_argument("--ocr-base", default="")
    p.add_argument("--structure-base", default="")
    p.add_argument(
        "--structure-mode",
        choices=["auto", "http", "inprocess"],
        default="http",
        help="StructureV3 transport (default http = official POST /layout-parsing).",
    )
    p.add_argument("--qwen-base", default="")
    p.add_argument("--qwen-model", default="")
    p.add_argument(
        "--from-dir",
        default="",
        help="Directory with prior report.json containing ocr + structure arms (json-compare).",
    )
    p.add_argument(
        "--no-structure-llm",
        action="store_true",
        help="Deprecated no-op: structure arm never runs LLM (use json-compare).",
    )
    p.add_argument("--output-dir", default="")
    p.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit non-zero if any arm fails.",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
