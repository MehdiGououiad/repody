#!/usr/bin/env python3
"""Compare OCR text→JSON: better Qwen prompts vs IE-tuned NuExtract-2.0-2B.

Uses OCR front/back markdown already saved in a prior report (--from-dir).
Does not start OCR again.

Example:
  uv run python scripts/research/cnie_text_ie_compare.py --from-dir ../benchmark-reports/cnie-structure-llm/json-compare-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from repody.benchmarking.ocr import score_gououiad_cnie_fields

ROOT = Path(__file__).resolve().parents[2]
EXPECTATIONS = (
    ROOT / "e2e" / "fixtures" / "documents" / "gououiad-cnie.ocr-expectations.json"
)
_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

# Fair field prompts — what to extract, no expected values.
FRONT_PROMPTS = {
    "national_id": "National identity number (N° / CIN) on the front.",
    "first_name": "Given name (prénom) in Latin script.",
    "last_name": "Family name (nom) in Latin script.",
    "dob_1998": "Four-digit birth year only.",
    "dob_full": "Full date of birth as printed.",
    "valid_2035": "Card valid-until / expiry date as printed.",
    "can_serial": "CAN serial digits as printed.",
    "birth_place": "Place of birth as printed.",
    "document_title": "French document title line.",
    "kingdom_header": "French kingdom / country header.",
    "arabic_first": "Given name in Arabic script.",
}
BACK_PROMPTS = {
    "national_id": "National identity number (CIN) on the back.",
    "father_name": "Father name after Fils de / equivalent.",
    "mother_name": "Mother name after Et de / equivalent.",
    "address_city": "City from the address block.",
    "address_street": "Street name from the address block.",
    "gender": "Sex / gender code.",
    "mrz_line1_prefix": "MRZ line 1 text (leading characters).",
    "mrz_line2_dob": "MRZ line 2 date-of-birth encoding.",
    "mrz_line2_expiry": "MRZ line 2 expiry encoding.",
    "mrz_line3_name": "MRZ name line (surname<<given).",
    "opi_code": "OPI internal code exactly as printed.",
    "etat_civil": "État civil registry number digits.",
    "address_number": "Street number from the address.",
}


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    fence = _JSON_FENCE.search(text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _flatten(data: dict[str, Any], keys: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in keys:
        value = data.get(key, "")
        if isinstance(value, dict):
            value = value.get("value", value)
        s = "" if value is None else str(value).strip()
        if s in {"—", "-", "null", "None"}:
            s = ""
        out[key] = s
    return out


def _load_ocr_texts(from_dir: Path) -> tuple[str, str]:
    report = json.loads((from_dir / "report.json").read_text(encoding="utf-8"))
    for arm in report.get("results") or []:
        if arm.get("arm") == "ocr" and not arm.get("error"):
            return str(arm["front_markdown"]), str(arm["back_markdown"])
    raise RuntimeError(f"No successful ocr arm in {from_dir / 'report.json'}")


def _template(prompts: dict[str, str]) -> dict[str, str]:
    # Official NuExtract leaf type for plain strings.
    return {k: "string" for k in prompts}


async def qwen_better(
    client: httpx.AsyncClient,
    *,
    base: str,
    model: str,
    prompts: dict[str, str],
    text: str,
    side: str,
) -> tuple[dict[str, str], str]:
    keys = ", ".join(f'"{k}"' for k in prompts)
    field_lines = "\n".join(f'- "{k}": {v}' for k, v in prompts.items())
    system = (
        "/no_think\n"
        "You extract identity-card fields from OCR text into JSON.\n"
        "Rules:\n"
        "1) Reply with one flat JSON object only.\n"
        f"2) Keys must be exactly: {keys}\n"
        "3) Copy values VERBATIM from the OCR text — do not truncate codes, "
        "IDs, OPI strings, or MRZ segments.\n"
        "4) If a value is missing, use an empty string.\n"
        "5) Do not invent values."
    )
    user = (
        f"Side: {side} of a Moroccan CNIE.\n"
        f"Fields:\n{field_lines}\n\n"
        f"OCR text:\n{text}\n\n"
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
    res = await client.post(f"{base.rstrip('/')}/chat/completions", json=payload)
    res.raise_for_status()
    raw = str(res.json()["choices"][0]["message"]["content"] or "")
    return _flatten(_parse_json_object(raw), list(prompts)), raw


async def nuextract2_text(
    client: httpx.AsyncClient,
    *,
    base: str,
    model: str,
    prompts: dict[str, str],
    text: str,
) -> tuple[dict[str, str], str]:
    # Official llama.cpp NuExtract-2.0 text IE format (manual template).
    template = json.dumps(_template(prompts), ensure_ascii=False, indent=4)
    content = f"# Template:\n{template}\n{text}"
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 768,
        "messages": [{"role": "user", "content": content}],
    }
    res = await client.post(f"{base.rstrip('/')}/chat/completions", json=payload)
    res.raise_for_status()
    msg = res.json()["choices"][0]["message"]
    raw = str(msg.get("content") or msg.get("reasoning_content") or "")
    return _flatten(_parse_json_object(raw), list(prompts)), raw


async def run_model(
    name: str,
    extract,
) -> dict[str, Any]:
    started = time.perf_counter()
    front_fields, front_raw = await extract("front", FRONT_PROMPTS)
    front_ms = int((time.perf_counter() - started) * 1000)
    started = time.perf_counter()
    back_fields, back_raw = await extract("back", BACK_PROMPTS)
    back_ms = int((time.perf_counter() - started) * 1000)
    score = score_gououiad_cnie_fields(front_fields, back_fields)
    return {
        "arm": name,
        "elapsed_ms": {"front": front_ms, "back": back_ms, "total": front_ms + back_ms},
        "front_fields": front_fields,
        "back_fields": back_fields,
        "front_raw": front_raw[:3000],
        "back_raw": back_raw[:3000],
        "score": {
            "total_score": score["total_score"],
            "total_max": score["total_max"],
            "core_score": score["core_score"],
            "core_max": score["core_max"],
            "hard_score": score["hard_score"],
            "hard_max": score["hard_max"],
            "cin_hit": score["cin_hit"],
            "mrz_hit": score["mrz_hit"],
            "hits": score["hits"],
        },
    }


async def main_async(args: argparse.Namespace) -> int:
    from_dir = Path(args.from_dir)
    front_md, back_md = _load_ocr_texts(from_dir)
    out_dir = Path(args.output_dir) if args.output_dir else from_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    qwen_base = args.qwen_base or "http://127.0.0.1:8084/v1"
    qwen_model = args.qwen_model or "Qwen3.5-4B"
    ne_base = args.nuextract2_base or "http://127.0.0.1:8085/v1"
    ne_model = args.nuextract2_model or "NuExtract-2.0-2B"

    results: list[dict[str, Any]] = []
    timeout = httpx.Timeout(300.0, connect=30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        if args.arm in {"qwen-better", "both"}:
            print("==> qwen-better (improved prompts on OCR text)")

            async def qwen_extract(side: str, prompts: dict[str, str]):
                text = front_md if side == "front" else back_md
                return await qwen_better(
                    client,
                    base=qwen_base,
                    model=qwen_model,
                    prompts=prompts,
                    text=text,
                    side=side,
                )

            try:
                result = await run_model("qwen-better", qwen_extract)
                results.append(result)
                s = result["score"]
                print(
                    f"    {s['total_score']}/{s['total_max']} "
                    f"(opi={result['back_fields'].get('opi_code')!r})"
                )
            except Exception as exc:
                print(f"    FAILED: {exc}")
                results.append({"arm": "qwen-better", "error": repr(exc)})

        if args.arm in {"nuextract2", "both"}:
            print("==> nuextract2 (IE-tuned NuExtract-2.0-2B on OCR text)")

            async def ne_extract(side: str, prompts: dict[str, str]):
                text = front_md if side == "front" else back_md
                return await nuextract2_text(
                    client,
                    base=ne_base,
                    model=ne_model,
                    prompts=prompts,
                    text=text,
                )

            try:
                result = await run_model("ocr-nuextract2", ne_extract)
                results.append(result)
                s = result["score"]
                print(
                    f"    {s['total_score']}/{s['total_max']} "
                    f"(opi={result['back_fields'].get('opi_code')!r})"
                )
            except Exception as exc:
                print(f"    FAILED: {exc}")
                results.append({"arm": "ocr-nuextract2", "error": repr(exc)})

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_ocr_dir": str(from_dir),
        "front_prompts": FRONT_PROMPTS,
        "back_prompts": BACK_PROMPTS,
        "results": results,
    }
    out = out_dir / "text-ie-compare.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out}")

    lines = [
        "# OCR text → JSON: Qwen better prompts vs NuExtract-2.0 IE",
        "",
        "| Arm | Total | Core | Hard | OPI field |",
        "|---|---:|---:|---:|---|",
    ]
    for arm in results:
        if arm.get("error"):
            lines.append(f"| {arm['arm']} | error | — | — | — |")
            continue
        s = arm["score"]
        lines.append(
            f"| {arm['arm']} | {s['total_score']}/{s['total_max']} | "
            f"{s['core_score']}/{s['core_max']} | {s['hard_score']}/{s['hard_max']} | "
            f"`{arm['back_fields'].get('opi_code','')}` |"
        )
    md = out_dir / "text-ie-compare.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {md}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--from-dir", required=True)
    p.add_argument("--output-dir", default="")
    p.add_argument("--arm", choices=["qwen-better", "nuextract2", "both"], default="both")
    p.add_argument("--qwen-base", default="")
    p.add_argument("--qwen-model", default="")
    p.add_argument("--nuextract2-base", default="")
    p.add_argument("--nuextract2-model", default="")
    args = p.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
