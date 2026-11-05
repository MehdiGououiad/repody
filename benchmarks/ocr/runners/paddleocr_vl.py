# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["paddlepaddle==3.2.1", "paddleocr[doc-parser]", "pypdfium2>=5.14", "pillow"]
#
# [[tool.uv.index]]
# name = "paddle-cpu"
# url = "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
# explicit = true
#
# [tool.uv.sources]
# paddlepaddle = { index = "paddle-cpu" }
# ///
"""PaddleOCR-VL-1.6 as in the PaddleOCR-VL usage tutorial: PaddlePaddle 3.2.1 CPU build with
`paddleocr[doc-parser]`, `PaddleOCRVL()` (pipeline_version v1.6 by default) running natively on the
CPU, which the hardware matrix marks supported for x64 CPU. The page is `save_to_markdown`'s Markdown.

    uv run runners/paddleocr_vl.py
"""

import tempfile
from pathlib import Path

from common import run
from paddleocr import PaddleOCRVL

# Equal footing: keep every label in the Markdown and read text inside image blocks (by default
# headers, footers, numbers, footnotes and side text are left out, and images are not read).
pipeline = PaddleOCRVL(pipeline_version="v1.6", device="cpu", markdown_ignore_labels=[], use_ocr_for_image_block=True)


def infer(page: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        for result in pipeline.predict(str(page)):
            result.save_to_markdown(save_path=tmp)
        return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(Path(tmp).rglob("*.md")))


run("paddleocr-vl-1.6", {"runtime": "paddleocr PaddleOCRVL v1.6, PaddlePaddle 3.2.1 CPU", "weights": "PaddlePaddle/PaddleOCR-VL-1.6"}, infer)
