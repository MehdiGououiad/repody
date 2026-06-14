from __future__ import annotations

from functools import lru_cache

from audit_workbench.inference.base import InferenceClient
from audit_workbench.inference.docker_model_runner import DockerModelRunnerInferenceClient
from audit_workbench.inference.stub import StubInferenceClient
from audit_workbench.settings import get_settings


@lru_cache
def get_inference_client() -> InferenceClient:
    settings = get_settings()
    mode = settings.inference_mode.lower()
    if mode == "docker_model_runner":
        return DockerModelRunnerInferenceClient(settings)
    return StubInferenceClient()
