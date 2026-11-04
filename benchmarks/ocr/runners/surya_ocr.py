# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["surya-ocr>=0.23.0", "pypdfium2>=5.14", "pillow"]
# ///
"""Surya OCR 2.5, following its model card's Python example: `SuryaInferenceManager` with the llama.cpp
backend (the documented CPU / non-NVIDIA path; it spawns the `llama-server` on PATH, here the Vulkan
build) and full-page `RecognitionPredictor`. The page is the blocks' HTML in reading order.

Licence: weights under a modified OpenRAIL-M (commercial use needs a Datalab licence above a size).
    uv run runners/surya_ocr.py
"""

import os

os.environ.setdefault("SURYA_INFERENCE_BACKEND", "llamacpp")
os.environ.setdefault("SURYA_INFERENCE_PARALLEL", "1")

from common import page_image, run  # noqa: E402
from surya.inference import SuryaInferenceManager  # noqa: E402
from surya.recognition import RecognitionPredictor  # noqa: E402

predictor = RecognitionPredictor(SuryaInferenceManager())


def infer(pdf) -> str:
    [page] = predictor([page_image(pdf, dpi=192)])
    blocks = sorted((b for b in page.blocks if not b.skipped), key=lambda b: b.reading_order)
    return "\n".join(b.html for b in blocks)


run("surya-ocr-2.5", {"runtime": "surya-ocr, llama.cpp b12098 Vulkan (auto-spawned)", "weights": "datalab-to/surya-ocr-2.5"}, infer)
