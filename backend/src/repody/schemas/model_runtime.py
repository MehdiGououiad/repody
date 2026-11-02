"""Model runtime configuration API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from repody.schemas.common import CamelModel

ConfigScope = Literal["platform", "worker_runtime", "inference_server"]
RestartTarget = Literal["worker", "api", "inference", "helm", "none"]


class ModelConfigField(CamelModel):
    key: str
    env_var: str
    label: str
    description: str
    scope: ConfigScope
    restart: RestartTarget
    value: str | int | float | bool | None = None
    configured: bool = True
    source: str = "platform"


class ModelRuntimeProfile(CamelModel):
    model_id: str
    label: str
    runtime: str
    runtime_model: str
    enabled: bool
    inference_url: str | None = None
    render_policy: str = ""
    fields: list[ModelConfigField] = Field(default_factory=list)


class DeploymentNote(CamelModel):
    change_kind: str
    action: str
    detail: str


class ModelRuntimeConfigResponse(CamelModel):
    models: list[ModelRuntimeProfile] = Field(default_factory=list)
    shared: list[ModelConfigField] = Field(default_factory=list)
    deployment_notes: list[DeploymentNote] = Field(default_factory=list)
