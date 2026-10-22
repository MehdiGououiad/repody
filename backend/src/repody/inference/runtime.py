from __future__ import annotations

from repody.settings import Settings, get_settings
from repody.util.urls import is_remote_inference_url

DOCUMENT_RUNTIME = "llamacpp"
NUEXTRACT_CLOUD_RUNTIME = "nuextract_cloud"
PADDLEOCR_V6_RUNTIME = "paddleocr_v6"
PADDLEOCR_QWEN_RUNTIME = "paddleocr_qwen"
GLM_OCR_RUNTIME = "glm_ocr"
GLM_OCR_QWEN_RUNTIME = "glm_ocr_qwen"


def llamacpp_base_url(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return settings.llamacpp_base_url.rstrip("/")


def openai_api_key_for_base_url(base_url: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if base_url.rstrip("/").startswith(llamacpp_base_url(settings)):
        return settings.llamacpp_api_key or "local"
    return "local"


def openai_probe_timeout_seconds(base_url: str, *, default: float = 2.0) -> float:
    """Remote inference may need extra time on first request after idle."""
    if is_remote_inference_url(base_url):
        return 30.0
    return default
