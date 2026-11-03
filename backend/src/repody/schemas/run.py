from repody.schemas.common import CamelModel


class RunAuditField(CamelModel):
    key: str
    description: str = ""
    value: str = ""
    type: str = "string"
    confidence: float | None = None
    extracted: bool = True
    flagged: bool = False


class RunDocumentExtractionMeta(CamelModel):
    extraction_ms: int = 0
    cache_hit: bool = False
    gpu_cold_start_likely: bool = False
    fields_extracted: int = 0
    markdown_text: str | None = None
    raw_text: str | None = None
    markdown_extraction: bool = False
    pages_rendered: int | None = None
    pages_sent: int | None = None
    pages_dropped: int | None = None


class RunAuditDocument(CamelModel):
    id: str
    document_type: str
    file_name: str | None = None
    fields: list[RunAuditField]
    extraction: RunDocumentExtractionMeta | None = None


class RunAuditRule(CamelModel):
    id: str
    name: str
    kind: str
    scope: str = "intra"
    status: str
    severity: str
    expression: str = ""
    affected_fields: list[str] = []
    detail: str = ""
    expected_value: str | None = None
    actual_value: str | None = None


class RunSummary(CamelModel):
    total: int
    passed: int
    failed: int
    fields_extracted: int


class RunAuditMetadata(CamelModel):
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    extraction_ms: int = 0
    validation_ms: int = 0


class RunAuditDetail(CamelModel):
    id: str
    workflow_id: str
    workflow_name: str
    status: str
    source: str
    created_at: str
    documents: list[RunAuditDocument]
    rule_results: list[RunAuditRule]
    summary: RunSummary
    metadata: RunAuditMetadata | None = None
