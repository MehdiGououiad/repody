"""Platform run contracts — frozen data only."""

from __future__ import annotations

from dataclasses import dataclass

from repody.schemas.workflow import DocumentDefSchema, WorkflowRuleSchema


@dataclass(frozen=True, slots=True)
class FileBinding:
    document_id: str | None
    storage_key: str
    mime_type: str = "application/octet-stream"
    file_name: str | None = None


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    documents: list[DocumentDefSchema]
    rules: list[WorkflowRuleSchema]
    workflow_name: str | None = None


@dataclass(frozen=True, slots=True)
class EnqueueRunRequest:
    workflow_id: str
    authorization: str | None = None
    file_bindings: list[FileBinding] | None = None
    snapshot: RunSnapshot | None = None
    client_host: str | None = None
    # True for bare POST /runs (production API shape without builder snapshot).
    production_api_shape: bool = False
