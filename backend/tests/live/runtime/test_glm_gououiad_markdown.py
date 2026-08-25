"""Live Gououiad CNIE hard test for GLM-OCR markdown adapter.

Calls the official SDK against AUDIT_GLM_OCR_BASE_URL (Ollama by default).
Scores OCR text against e2e/fixtures/documents/gououiad-cnie.ocr-expectations.json.

Enable the service first, then:

  $env:AUDIT_GLM_OCR_ENABLED = "true"
  $env:AUDIT_GLM_OCR_BASE_URL = "http://127.0.0.1:11434"
  $env:AUDIT_GLM_OCR_SERVED_MODEL = "glm-ocr:latest"
  $env:GLM_GOUOUIAD_LIVE = "1"
  pnpm glmocr:serve
  pnpm test:live -- tests/live/runtime/test_glm_gououiad_markdown.py -v -s
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
from scripts.benchmarking import score_gououiad_cnie_markdown

from repody.extraction.branding import GLM_OCR_CATALOG_ID
from repody.extraction.glm_ocr import extract_with_glm_ocr
from repody.extraction.types import DocumentBundle
from repody.infra.storage.mime import resolve_mime
from repody.settings import get_settings

pytestmark = [pytest.mark.live, pytest.mark.slow]

FIXTURES = Path(__file__).resolve().parents[4] / "e2e" / "fixtures" / "documents"
FRONT_PATH = FIXTURES / "gououiad-cnie-front.png"
BACK_PATH = FIXTURES / "gououiad-cnie-back.png"
REPORT_PATH = Path(__file__).resolve().parents[4] / "benchmark-reports" / "glm-gououiad-last.json"

MIN_CORE_RATIO = 0.40


def _live_requested() -> bool:
    return os.environ.get("GLM_GOUOUIAD_LIVE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _bundle(path: Path) -> DocumentBundle:
    data = path.read_bytes()
    mime = resolve_mime(data=data, declared=None)
    return DocumentBundle(raw_bytes=data, mime_type=mime)


def _health_url(base_url: str) -> str:
    """Ollama uses /api/tags; OpenAI-compat roots use /models under /v1."""
    raw = base_url.rstrip("/")
    path = (urlparse(raw if "://" in raw else f"http://{raw}").path or "").rstrip("/")
    if path.endswith("/v1"):
        return f"{raw}/models"
    return f"{raw}/api/tags"


async def _service_reachable(base_url: str) -> bool:
    url = _health_url(base_url)
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
    model: str,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    front_result = await extract_with_glm_ocr(front, [], "CNIE front")
    front_ms = int((time.perf_counter() - t0) * 1000)
    t1 = time.perf_counter()
    back_result = await extract_with_glm_ocr(back, [], "CNIE back")
    back_ms = int((time.perf_counter() - t1) * 1000)
    front_md = front_result.markdown_text or ""
    back_md = back_result.markdown_text or ""
    scored = score_gououiad_cnie_markdown(front_md, back_md, include_hard=True)
    return {
        "catalog_id": GLM_OCR_CATALOG_ID,
        "pack": "zai-org/GLM-OCR via Ollama",
        "model": model,
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
async def test_gououiad_glm_ocr_markdown():
    if not _live_requested():
        pytest.skip("Set GLM_GOUOUIAD_LIVE=1 to run Gououiad GLM-OCR hard test")

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.glm_ocr_enabled:
        pytest.skip("Set AUDIT_GLM_OCR_ENABLED=true")

    base = settings.glm_ocr_base_url
    health = _health_url(base)
    if not await _service_reachable(base):
        pytest.fail(f"GLM-OCR service not reachable at {health}")

    front = _bundle(FRONT_PATH)
    back = _bundle(BACK_PATH)

    try:
        report = await _run(
            front=front,
            back=back,
            model=settings.glm_ocr_served_model,
        )
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
            f"{GLM_OCR_CATALOG_ID} core_ratio={core_ratio:.2f} "
            f"< {MIN_CORE_RATIO} (see {REPORT_PATH})"
        )
        assert int(report.get("front_chars") or 0) > 0
        assert int(report.get("back_chars") or 0) > 0
    finally:
        get_settings.cache_clear()
