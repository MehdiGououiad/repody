from __future__ import annotations

from functools import lru_cache

from audit_workbench.inference.base import InferenceClient
from audit_workbench.inference.stub import StubInferenceClient
from audit_workbench.inference.validation_client import ValidationInferenceClient
from audit_workbench.settings import get_settings


@lru_cache
def get_inference_client() -> InferenceClient:
    settings = get_settings()
    if settings.inference_mode.lower() == "stub":
        return StubInferenceClient()
    return ValidationInferenceClient(settings)
