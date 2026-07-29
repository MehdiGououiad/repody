"""Request bodies for run creation and workflow test runs."""

from __future__ import annotations

from audit_workbench.runtime.run.contracts import FileBinding, RunSnapshot
from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.workflow import DocumentDefSchema, WorkflowRuleSchema


class RunSnapshotBody(CamelModel):
    """Ephemeral workflow config for a single run — does not mutate the saved workflow."""

    documents: list[DocumentDefSchema] = []
    rules: list[WorkflowRuleSchema] = []
    workflow_name: str | None = None

    def to_snapshot(self) -> RunSnapshot:
        return RunSnapshot(
            documents=self.documents,
            rules=self.rules,
            workflow_name=self.workflow_name,
        )


class StoredFileBinding(CamelModel):
    document_id: str | None = None
    storage_key: str
    mime_type: str
    file_name: str

    def to_binding(self) -> FileBinding:
        return FileBinding(
            document_id=self.document_id,
            storage_key=self.storage_key,
            mime_type=self.mime_type,
            file_name=self.file_name,
        )


class CreateRunJsonBody(CamelModel):
    snapshot: RunSnapshotBody | None = None
    file_bindings: list[StoredFileBinding] = []
