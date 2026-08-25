"""Register document-model adapters with the catalog (side-effect imports)."""

from __future__ import annotations

import repody.extraction.glm_ocr
import repody.extraction.glm_ocr_qwen
import repody.extraction.paddleocr_qwen
import repody.extraction.paddleocr_v6
import repody.extraction.vlm  # noqa: F401
