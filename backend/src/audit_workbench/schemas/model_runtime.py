"""Model runtime configuration API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from audit_workbench.schemas.common import CamelModel

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
    model_id: str = Field(serialization_alias="modelId")
    label: str
    runtime: str
    runtime_model: str = Field(serialization_alias="runtimeModel")
    enabled: bool
    inference_url: str | None = Field(default=None, serialization_alias="inferenceUrl")
    render_policy: str = Field(default="", serialization_alias="renderPolicy")
    fields: list[ModelConfigField] = Field(default_factory=list)


class DeploymentNote(CamelModel):
    change_kind: str = Field(serialization_alias="changeKind")
    action: str
    detail: str


class ModelRuntimeConfigResponse(CamelModel):
    models: list[ModelRuntimeProfile] = Field(default_factory=list)
    shared: list[ModelConfigField] = Field(default_factory=list)
    deployment_notes: list[DeploymentNote] = Field(
        default_factory=list, serialization_alias="deploymentNotes"
    )
