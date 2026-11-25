# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.28", "pypdfium2>=5.14", "pillow>=13.0"]
# ///
"""NuExtract3 (numind/NuExtract3-GGUF Q8_0) in Markdown mode, as Repody sends it: the page at 170 DPI,
`chat_template_kwargs={"mode": "markdown", "enable_thinking": False}`, temperature 0.

Needs the llama-server from `bun run llamacpp:serve` (http://127.0.0.1:8081).
    uv run runners/nuextract3.py
"""

import base64
import os

import httpx
from common import page_image, png, run

URL = "http://127.0.0.1:8081/v1/chat/completions"


def infer(pdf) -> str:
    image = base64.b64encode(png(page_image(pdf, dpi=170))).decode()
    body = {
        "model": "nuextract3-q8_0",
        "temperature": 0.0,
        "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}]}],
        "chat_template_kwargs": {"mode": "markdown", "enable_thinking": False},
    }
    response = httpx.post(URL, json=body, timeout=900)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"] or ""


# BENCH_NAME / BENCH_RUNTIME label a run on another server setup (see run_vulkan4.sh).
run(
    os.environ.get("BENCH_NAME", "nuextract3-q8_0"),
    {"runtime": os.environ.get("BENCH_RUNTIME", "llama.cpp b12098 Vulkan, Q8_0 (Repody's server flags)"), "weights": "numind/NuExtract3-GGUF"},
    infer,
)
