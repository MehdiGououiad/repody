# /// script
# requires-python = "==3.12.*"
# dependencies = ["minicpm-ocr[all]", "paddlepaddle==3.3.0", "pypdfium2>=5.14", "pillow"]
#
# [[tool.uv.index]]
# name = "paddle-cpu"
# url = "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
# explicit = true
#
# [tool.uv.sources]
# paddlepaddle = { index = "paddle-cpu" }
# ///
"""MiniCPM-OCR 1.0, following openbmb/MiniCPM-OCR-1.0-gguf: the official SDK (PP-DocLayoutV3 layout on
CPU, then each region recognised by the model) against a llama.cpp service started as the card says:

    llama-server -m MiniCPM-OCR-1_0-Q8_0.gguf --mmproj mmproj-model-f16-4x.gguf --port 18499 \
        --alias minicpm-ocr --ctx-size 8192 --parallel 1 --jinja --reasoning off -ngl 99

PaddlePaddle 3.3.0 (the tutorial's version), CPU build, for the documented CPU layout detection.
SDK settings from the card: backend llamacpp, engine.max_model_len 8192, one worker, serial queue,
no layout overlap. The page is the SDK's Markdown.
    uv run runners/minicpm_ocr.py
"""

import os
import tempfile
from importlib.resources import files
from pathlib import Path

from common import ROOT, run
from minicpmvocr import load_config, pipelined_run
from minicpmvocr.layouts.download import ensure_layout_model

LAYOUT = ensure_layout_model(ROOT / ".models" / "PP-DocLayoutV3_infer")


def infer(pdf: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = load_config(
            str(files("minicpmvocr").joinpath("configs/minicpmvocr.yaml")),
            overrides={
                "input": {"file_path": str(pdf)},
                "engine": {"type": "llamacpp", "server_url": "http://127.0.0.1:18499", "model_name": "minicpm-ocr", "max_model_len": 8192},
                "layout": {"model_dir": str(LAYOUT), "device": "cpu"},
                "pipeline": {"overlap_layout": False, "queue_mode": "serial"},
                "run": {"run_root": tmp, "workers": 1},
            },
        )
        pipelined_run(cfg)
        return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(Path(cfg["_meta"]["output_dir"]).rglob("*.md")))


# BENCH_VARIANT=dspark when the service runs with the DSpark draft head (see run_dspark.sh).
VARIANT = os.environ.get("BENCH_VARIANT", "")
run(
    f"minicpm-ocr-1.0{'-' + VARIANT if VARIANT else ''}",
    {"runtime": f"minicpm-ocr SDK (layout CPU) + llama.cpp b12098 Vulkan, Q8_0{' + DSpark draft' if VARIANT else ''}", "weights": "openbmb/MiniCPM-OCR-1.0-gguf"},
    infer,
)
