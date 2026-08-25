"""Live Gououiad CNIE hard test for PP-OCRv6 markdown adapter.

Calls the PP-OCRv6 HTTP service directly (no full workflow stack). Scores OCR
text against e2e/fixtures/documents/gououiad-cnie.ocr-expectations.json.

Enable the service first, then:

  $env:AUDIT_PADDLEOCR_V6_ENABLED = "true"
  $env:AUDIT_PADDLEOCR_V6_BASE_URL = "http://127.0.0.1:8868"
  $env:PADDLEOCR_GOUOUIAD_LIVE = "1"
  pnpm test:live -- tests/live/runtime/test_paddleocr_gououiad_markdown.py -v -s
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from scripts.benchmarking import score_gououiad_cnie_markdown

from repody.extraction.branding import PADDLEOCR_V6_CATALOG_ID
from repody.extraction.paddleocr_v6 import extract_with_paddleocr_v6
from repody.extraction.types import DocumentBundle
from repody.infra.storage.mime import resolve_mime
from repody.settings import get_settings

pytestmark = [pytest.mark.live, pytest.mark.slow]

FIXTURES = Path(__file__).resolve().parents[4] / "e2e" / "fixtures" / "documents"
FRONT_PATH = FIXTURES / "gououiad-cnie-front.png"
BACK_PATH = FIXTURES / "gououiad-cnie-back.png"
REPORT_PATH = (
    Path(__file__).resolve().parents[4] / "benchmark-reports" / "paddleocr-gououiad-last.json"
)

MIN_CORE_RATIO_V6 = 0.40


def _live_requested() -> bool:
    return os.environ.get("PADDLEOCR_GOUOUIAD_LIVE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _bundle(path: Path) -> DocumentBundle:
    data = path.read_bytes()
    mime = resolve_mime(data=data, declared=None)
    return DocumentBundle(raw_bytes=data, mime_type=mime)


async def _service_reachable(base_url: str, path: str) -> bool:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Empty body should still hit the route (4xx/422 ok; connection fail = skip).
            response = await client.post(url, json={})
        return response.status_code < 500 or response.status_code in {400, 422}
    except (httpx.HTTPError, OSError):
        return False


async def _run_v6(
    *,
    front: DocumentBundle,
    back: DocumentBundle,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    front_result = await extract_with_paddleocr_v6(front, [], "CNIE front")
    front_ms = int((time.perf_counter() - t0) * 1000)
    t1 = time.perf_counter()
    back_result = await extract_with_paddleocr_v6(back, [], "CNIE back")
    back_ms = int((time.perf_counter() - t1) * 1000)
    front_md = front_result.markdown_text or ""
    back_md = back_result.markdown_text or ""
    scored = score_gououiad_cnie_markdown(front_md, back_md, include_hard=True)
    return {
        "catalog_id": PADDLEOCR_V6_CATALOG_ID,
        "front_ms": front_ms,
        "back_ms": back_ms,
        "wall_ms": front_ms + back_ms,
        "front_chars": len(front_md),
        "back_chars": len(back_md),
        "front_preview": front_md[:800],
        "back_preview": back_md[:800],
        "score": scored,
    }


@pytest.mark.asyncio
async def test_gououiad_paddleocr_v6_markdown():
    if not _live_requested():
        pytest.skip("Set PADDLEOCR_GOUOUIAD_LIVE=1 to run Gououiad PP-OCRv6 hard test")

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.paddleocr_v6_enabled:
        pytest.skip("Set AUDIT_PADDLEOCR_V6_ENABLED=true")

    base = settings.paddleocr_v6_base_url
    if not await _service_reachable(base, "/ocr"):
        pytest.fail(f"PP-OCRv6 service not reachable at {base}/ocr")

    front = _bundle(FRONT_PATH)
    back = _bundle(BACK_PATH)

    try:
        report = await _run_v6(front=front, back=back)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"models": [report]}
        REPORT_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        print(json.dumps(payload, indent=2, ensure_ascii=True))

        score = report["score"]
        core_max = int(score.get("core_max") or 0) or 1
        core_ratio = float(score.get("core_score") or 0) / core_max
        assert core_ratio >= MIN_CORE_RATIO_V6, (
            f"{PADDLEOCR_V6_CATALOG_ID} core_ratio={core_ratio:.2f} "
            f"< {MIN_CORE_RATIO_V6} (see {REPORT_PATH})"
        )
        assert int(report.get("front_chars") or 0) > 0
        assert int(report.get("back_chars") or 0) > 0
    finally:
        get_settings.cache_clear()
