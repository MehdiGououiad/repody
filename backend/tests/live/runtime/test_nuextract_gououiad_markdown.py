"""Live Gououiad CNIE hard test for NuExtract (repody:vlm) markdown path.

Calls llama-server on AUDIT_LLAMACPP_BASE_URL directly (no full workflow stack).
Scores OCR text against e2e/fixtures/documents/gououiad-cnie.ocr-expectations.json.

Enable the service first, then:

  $env:NUEXTRACT_GOUOUIAD_LIVE = "1"
  pnpm llamacpp:serve
  pnpm test:live -- tests/live/runtime/test_nuextract_gououiad_markdown.py -v -s
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from repody.benchmarking import score_gououiad_cnie_markdown
from repody.extraction.branding import REPODY_VLM_CATALOG_ID
from repody.extraction.types import DocumentBundle
from repody.extraction.vlm import extract_with_repody_vlm
from repody.infra.storage.mime import resolve_mime
from repody.settings import get_settings

pytestmark = [pytest.mark.live, pytest.mark.slow]

FIXTURES = Path(__file__).resolve().parents[4] / "e2e" / "fixtures" / "documents"
FRONT_PATH = FIXTURES / "gououiad-cnie-front.png"
BACK_PATH = FIXTURES / "gououiad-cnie-back.png"
REPORT_PATH = (
    Path(__file__).resolve().parents[4]
    / "benchmark-reports"
    / "nuextract-gououiad-markdown-last.json"
)

MIN_CORE_RATIO = 0.40


def _live_requested() -> bool:
    return os.environ.get("NUEXTRACT_GOUOUIAD_LIVE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _bundle(path: Path) -> DocumentBundle:
    data = path.read_bytes()
    mime = resolve_mime(data=data, declared=None)
    return DocumentBundle(raw_bytes=data, mime_type=mime)


async def _service_reachable(base_url: str) -> bool:
    url = f"{base_url.rstrip('/')}/models"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
        return response.status_code < 500
    except (httpx.HTTPError, OSError):
        return False


async def _run(
    *,
    front: DocumentBundle,
    back: DocumentBundle,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    front_result = await extract_with_repody_vlm(
        front,
        [],
        "CNIE front",
        markdown_extraction=True,
    )
    front_ms = int((time.perf_counter() - t0) * 1000)
    t1 = time.perf_counter()
    back_result = await extract_with_repody_vlm(
        back,
        [],
        "CNIE back",
        markdown_extraction=True,
    )
    back_ms = int((time.perf_counter() - t1) * 1000)
    front_md = front_result.markdown_text or ""
    back_md = back_result.markdown_text or ""
    scored = score_gououiad_cnie_markdown(front_md, back_md, include_hard=True)
    return {
        "catalog_id": REPODY_VLM_CATALOG_ID,
        "pack": "numind/NuExtract3-GGUF",
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
async def test_gououiad_nuextract_markdown(monkeypatch: pytest.MonkeyPatch):
    if not _live_requested():
        pytest.skip("Set NUEXTRACT_GOUOUIAD_LIVE=1 to run Gououiad NuExtract markdown hard test")

    # conftest pins a mock LLAMACPP URL; live hard tests need the real host server.
    monkeypatch.setenv("AUDIT_LLAMACPP_BASE_URL", "http://127.0.0.1:8081/v1")
    monkeypatch.setenv("AUDIT_REPODY_VLM_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.repody_vlm_enabled:
        pytest.skip("Set AUDIT_REPODY_VLM_ENABLED=true")

    base = settings.llamacpp_base_url
    if not await _service_reachable(base):
        pytest.fail(f"NuExtract llama-server not reachable at {base}/models")

    front = _bundle(FRONT_PATH)
    back = _bundle(BACK_PATH)

    try:
        report = await _run(front=front, back=back)
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
        assert core_ratio >= MIN_CORE_RATIO, (
            f"{REPODY_VLM_CATALOG_ID} core_ratio={core_ratio:.2f} "
            f"< {MIN_CORE_RATIO} (see {REPORT_PATH})"
        )
        assert int(report.get("front_chars") or 0) > 0
        assert int(report.get("back_chars") or 0) > 0
    finally:
        get_settings.cache_clear()
