from __future__ import annotations

import os
from functools import lru_cache
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from audit_workbench.settings.fields_auth import AuthSettingsFields
from audit_workbench.settings.fields_core import CoreSettingsFields
from audit_workbench.settings.fields_inference import InferenceSettingsFields
from audit_workbench.settings.fields_ops import OpsSettingsFields
from audit_workbench.settings.fields_storage import StorageSettingsFields
from audit_workbench.settings.fields_workers import WorkerSettingsFields
from audit_workbench.settings.validators import (
    apply_inference_probe_defaults,
    validate_production_guardrails,
    validate_timeout_alignment,
)


class Settings(
    BaseSettings,
    CoreSettingsFields,
    WorkerSettingsFields,
    AuthSettingsFields,
    StorageSettingsFields,
    InferenceSettingsFields,
    OpsSettingsFields,
):
    model_config = SettingsConfigDict(
        env_prefix="AUDIT_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def _sync_validation_options(self) -> Self:
        if self.llm_validation_enabled and not self.structured_llm_enabled:
            self.structured_llm_enabled = True
        if self.oidc_enabled and not self.oidc_issuer:
            raise ValueError("AUDIT_OIDC_ISSUER is required when AUDIT_OIDC_ENABLED=true.")
        if not self.vllm_api_key:
            self.vllm_api_key = os.getenv("AUDIT_VLLM_API_KEY", "").strip() or None
        apply_inference_probe_defaults(self)
        validate_production_guardrails(self)
        validate_timeout_alignment(self)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
