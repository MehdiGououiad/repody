# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["mineru>=4.0,<5", "pypdfium2>=5.14", "pillow"]
# ///
"""MinerU 4 (MinerU2.5-Pro VLM) as its README: the base install (ONNX + llama.cpp engines, "CPU works,
Vulkan recommended"; here the VLM runs on llama.cpp Vulkan and small models on ONNX DirectML) and
`mineru-kit parse <file> -o <file>.md --tier standard`, the default tier for normal reading.

MINERU_FORMAT=markdown (default) scores that Markdown, which leaves out headers and footers;
MINERU_FORMAT=middle_json scores every block of the documented `--format middle_json` output in order.

    uv run runners/mineru.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from common import run

KIT = Path(sys.executable).with_name("mineru-kit.exe" if sys.platform == "win32" else "mineru-kit")
FORMAT = os.environ.get("MINERU_FORMAT", "markdown")


def block_text(block: dict) -> str:
    """A middle_json block's content: text spans and table HTML, nested items included."""
    parts = []
    for item in block.get("content") or []:
        if isinstance(item, dict):
            content = item.get("content")
            parts.append(block_text(item) if isinstance(content, list) else str(content or ""))
    return "\n".join(p for p in parts if p)


def infer(page: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        if FORMAT == "markdown":
            out = Path(tmp) / f"{page.stem}.md"
            subprocess.run([str(KIT), "parse", str(page), "-o", str(out), "--tier", "standard"], check=True)
            return out.read_text(encoding="utf-8")
        out = Path(tmp) / f"{page.stem}.json"
        cmd = [str(KIT), "parse", str(page), "-o", str(out), "--tier", "standard", "--format", "middle_json"]
        subprocess.run(cmd, check=True)
        doc = json.loads(out.read_text(encoding="utf-8"))
        blocks = [b for p in doc["pages"] for b in sorted(p["blocks"], key=lambda b: b.get("index", 0))]
        return "\n\n".join(t for t in (block_text(b) for b in blocks) if t)


run(
    f"mineru-4-standard-{FORMAT}",
    {"runtime": f"mineru-kit 4.1.7 --tier standard, {FORMAT} (llama.cpp Vulkan + ONNX DirectML)", "weights": "opendatalab/MinerU2.5-Pro"},
    infer,
)
