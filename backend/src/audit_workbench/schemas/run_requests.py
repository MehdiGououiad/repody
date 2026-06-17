"""Request bodies for run creation and workflow test runs."""

from __future__ import annotations

from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.workflow import DocumentDefSchema, WorkflowRuleSchema


class RunSnapshotBody(CamelModel):
    """Ephemeral workflow config for a single run — does not mutate the saved workflow."""

    documents: list[DocumentDefSchema] = []
    rules: list[WorkflowRuleSchema] = []
    workflow_name: str | None = None


class StoredFileBinding(CamelModel):
    document_id: str | None = None
    storage_key: str
    mime_type: str
    file_name: str


class CreateRunJsonBody(CamelModel):
    snapshot: RunSnapshotBody | None = None
    file_bindings: list[StoredFileBinding] = []
