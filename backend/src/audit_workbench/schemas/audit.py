from audit_workbench.schemas.common import CamelModel


class AuditListItem(CamelModel):
    id: str
    status: str
    workflow_id: str
    workflow_name: str
    entity: str
    timestamp: str
    rows: int | None = None
    failed_rules: int | None = None


class AuditListResponse(CamelModel):
    audits: list[AuditListItem]
    total: int
    limit: int
    offset: int


class AuditDetailResponse(CamelModel):
    audit: AuditListItem
