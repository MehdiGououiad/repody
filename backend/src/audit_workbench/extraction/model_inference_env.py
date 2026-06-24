"""Central inference env mapping — only variables documented by each model upstream."""

from __future__ import annotations

from audit_workbench.settings import Settings

# Surya: https://huggingface.co/datalab-to/surya-ocr-2#inference-backends
SURYA_INFERENCE_ENV_KEYS = (
    "SURYA_INFERENCE_BACKEND",
    "SURYA_INFERENCE_URL",
    "SURYA_INFERENCE_PARALLEL",
    "IMAGE_DPI",
    "IMAGE_DPI_HIGHRES",
    "SURYA_MAX_TOKENS_FULL_PAGE",
    "DETECTOR_TEXT_THRESHOLD",
)


def surya_inference_env(settings: Settings, *, inference_url: str) -> dict[str, str]:
    return {
        "SURYA_INFERENCE_BACKEND": (settings.surya_inference_backend or "llamacpp").strip(),
        "SURYA_INFERENCE_PARALLEL": str(settings.surya_inference_parallel),
        "SURYA_INFERENCE_URL": inference_url,
        "IMAGE_DPI": str(settings.surya_image_dpi),
        "IMAGE_DPI_HIGHRES": str(settings.surya_image_dpi_highres),
        "SURYA_MAX_TOKENS_FULL_PAGE": str(settings.surya_max_tokens_full_page),
        "DETECTOR_TEXT_THRESHOLD": str(settings.surya_detector_text_threshold),
    }
