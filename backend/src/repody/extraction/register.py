"""Register document-model adapters with the catalog (side-effect imports)."""

from __future__ import annotations

from repody.extraction import glm_ocr_qwen as _glm_ocr_qwen
from repody.extraction import paddleocr_qwen as _paddleocr_qwen
from repody.extraction import vlm as _vlm

_ = (_glm_ocr_qwen, _paddleocr_qwen, _vlm)
