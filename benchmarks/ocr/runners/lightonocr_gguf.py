# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.28", "pypdfium2>=5.14", "pillow>=13.0"]
# ///
"""LightOnOCR-3-4B, GGUF build prithivMLmods/LightOnOCR-3-4B-GGUF (Q4_K_M, the card's default) served by
llama.cpp as that card shows (`llama serve -hf prithivMLmods/LightOnOCR-3-4B-GGUF:Q4_K_M`; here
`llama-server -hf ...`, which also fetches the mmproj). Requests follow LightOnOCR-3's model card: the
page rendered at 400 DPI with its longest edge at 2048 px, the image alone (transcription), thinking
off, temperature 0.2, top_p 0.9, max_tokens 4096.

    llama-server -hf prithivMLmods/LightOnOCR-3-4B-GGUF:Q8_0 --port 18501   # LIGHTON_QUANT=Q8_0
    uv run runners/lightonocr_gguf.py
"""

import base64
import os

import httpx
from common import page_image, png, run

URL = "http://127.0.0.1:18501/v1/chat/completions"


def infer(page) -> str:
    image = base64.b64encode(png(page_image(page, dpi=400, long_edge=2048))).decode()
    body = {
        "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}]}],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 4096,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    response = httpx.post(URL, json=body, timeout=1800)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"] or ""


QUANT = os.environ.get("LIGHTON_QUANT", "Q8_0")
run(f"lightonocr-3-4b-{QUANT.lower()}", {"runtime": f"llama.cpp b12098 Vulkan, {QUANT} (prithivMLmods GGUF)", "weights": "lightonai/LightOnOCR-3-4B"}, infer)
