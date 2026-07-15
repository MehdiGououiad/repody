"""Official NuExtract3-GGUF extraction contract — fixed values, not platform config."""

from __future__ import annotations

from audit_workbench.settings import Settings

# https://huggingface.co/numind/NuExtract3-GGUF
NUEXTRACT_PDF_DPI = 170
NUEXTRACT_ENABLE_THINKING = False
NUEXTRACT_MAX_PAGES_PER_REQUEST = 6


def extraction_inference_profile_key(*, settings: Settings) -> str:
    served_model = (settings.llamacpp_served_model or "").strip().lower()
    return f"nuextract:official:model:{served_model or 'default'}"
