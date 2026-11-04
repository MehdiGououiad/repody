"""Shared by the runners: the benchmark pages as images, and a timed loop that saves each output."""

from __future__ import annotations

import io
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOCS, OUT = ROOT / "docs", ROOT / "outputs"


def pages() -> list[Path]:
    only = set(sys.argv[1:])
    files = [p for p in sorted(DOCS.iterdir()) if p.suffix in (".pdf", ".png")]
    return [p for p in files if not only or p.stem in only]


def page_image(pdf: Path, dpi: int = 170, long_edge: int | None = None) -> Image.Image:
    """A PDF page rendered at `dpi`, or an image file as it is; then capped to `long_edge`."""
    if pdf.suffix != ".pdf":
        image = Image.open(pdf).convert("RGB")
    else:
        with pdfium.PdfDocument(pdf) as doc:
            image = doc[0].render(scale=dpi / 72).to_pil().convert("RGB")
    if long_edge and max(image.size) > long_edge:
        image.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)
    return image


def png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def run(model: str, meta: dict, infer: Callable[[Path], str], *, warmup: bool = True) -> None:
    """Infer every page (after one warm-up page), saving outputs/<model>/<page>.txt and the seconds."""
    out = OUT / model
    out.mkdir(parents=True, exist_ok=True)
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    timings_file = out / "timings.json"
    timings = json.loads(timings_file.read_text()) if timings_file.exists() else {}
    todo = pages()
    if warmup and todo:
        infer(todo[0])
    for pdf in todo:
        started = time.perf_counter()
        try:
            text = infer(pdf)
        except Exception as exc:  # a failed page scores zero; the run goes on
            print(f"{pdf.stem}: FAILED {type(exc).__name__}: {exc}", flush=True)
            continue
        timings[pdf.stem] = round(time.perf_counter() - started, 2)
        (out / f"{pdf.stem}.txt").write_text(text, encoding="utf-8")
        timings_file.write_text(json.dumps(timings, indent=1), encoding="utf-8")
        print(f"{pdf.stem}: {timings[pdf.stem]} s, {len(text)} chars", flush=True)
