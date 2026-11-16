"""The real documents through Repody's own extraction code (Markdown mode), for the benchmark.

    cd backend && uv run python ../benchmarks/ocr/via_repody.py

Uses repody.extraction.pipeline.extract (NuExtract3's Markdown mode) against the server started by
`pnpm llamacpp:serve` (:8081). Writes outputs/repody-nuextract/<page>.txt and timings.json, like the
runners.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

os.environ.update(
    AUDIT_LLAMACPP_BASE_URL="http://127.0.0.1:8081/v1",
    AUDIT_LLAMACPP_SERVED_MODEL="nuextract3-q8_0",
    AUDIT_INFERENCE_TIMEOUT_SECONDS="900",
    AUDIT_RUN_TIMEOUT_MINUTES="20",
)

from repody.extraction.pipeline import extract  # noqa: E402
from repody.schemas.workflow import DocumentDef  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "repody-nuextract"


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "meta.json").write_text(json.dumps({"runtime": "Repody pipeline, NuExtract3 Markdown mode"}))
    doc = DocumentDef(id="doc", document_type="Document", markdown_extraction=True)
    pages = sorted((HERE / "docs").glob("*__real.png"))
    await extract(doc, pages[0].read_bytes(), "image/png")  # warm-up
    timings = {}
    for page in pages:
        started = time.perf_counter()
        _, meta = await extract(doc, page.read_bytes(), "image/png")
        timings[page.stem] = round(time.perf_counter() - started, 2)
        (OUT / f"{page.stem}.txt").write_text(meta.markdown_text or "", encoding="utf-8")
        (OUT / "timings.json").write_text(json.dumps(timings, indent=1))
        print(f"{page.stem}: {timings[page.stem]} s, {len(meta.markdown_text or '')} chars", flush=True)


asyncio.run(main())
