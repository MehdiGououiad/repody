# /// script
# requires-python = ">=3.12"
# dependencies = ["rapidfuzz>=3.14"]
# ///
"""Lenient score of each model on each real document (pages ending in `__real`).

    uv run real_scores.py [model ...]     # default: every model in outputs/
"""

import json
import sys
from pathlib import Path

import score

HERE = Path(__file__).resolve().parent
pages = sorted(p.stem for p in (HERE / "gold").glob("*__real.json"))
models = sys.argv[1:] or sorted(p.name for p in (HERE / "outputs").iterdir() if p.is_dir())

print("| Model | Mean | " + " | ".join(p.removesuffix("__real") for p in pages) + " | s/page |")
print("|---" * (len(pages) + 3) + "|")
for model in models:
    folder = HERE / "outputs" / model
    timings = json.loads((folder / "timings.json").read_text()) if (folder / "timings.json").exists() else {}
    scores = []
    for page in pages:
        out = folder / f"{page}.txt"
        raw = out.read_text(encoding="utf-8") if out.exists() else ""
        gold = json.loads((HERE / "gold" / f"{page}.json").read_text(encoding="utf-8"))
        scores.append(score.score_page(gold, raw, lenient=True)["score"])
    real_times = sorted(timings[p] for p in pages if p in timings)
    median = f"{real_times[len(real_times) // 2]:.0f}" if real_times else "—"
    cells = " | ".join(f"{100 * s:.0f}" for s in scores)
    print(f"| {model} | **{100 * sum(scores) / len(scores):.1f}** | {cells} | {median} |")
