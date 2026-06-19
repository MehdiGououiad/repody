from pydantic import Field

from audit_workbench.schemas.common import CamelModel


class RunAuditField(CamelModel):
    key: str
    description: str = ""
    value: str = ""
    type: str = "string"
    confidence: float | None = None
    extracted: bool = True
    flagged: bool = False


class RunDocumentExtractionMeta(CamelModel):
    read_path_config: str = Field(serialization_alias="readPathConfig")
    read_path_used: str = Field(serialization_alias="readPathUsed")
    read_path_label: str = Field(serialization_alias="readPathLabel")
    validation_mode: str = Field(serialization_alias="validationMode")
    validation_label: str = Field(serialization_alias="validationLabel")
    ocr_model: str | None = Field(default=None, serialization_alias="ocrModel")
    llm_model: str | None = Field(default=None, serialization_alias="llmModel")
    extraction_ms: int = Field(default=0, serialization_alias="extractionMs")
    combined_llm: bool = Field(default=False, serialization_alias="combinedLlm")
    cache_hit: bool = Field(default=False, serialization_alias="cacheHit")
    gpu_cold_start_likely: bool = Field(default=False, serialization_alias="gpuColdStartLikely")
    ocr_skipped: bool = Field(default=False, serialization_alias="ocrSkipped")
    fields_extracted: int = Field(default=0, serialization_alias="fieldsExtracted")
    ocr_text: str | None = Field(default=None, serialization_alias="ocrText")
    pages_rendered: int | None = Field(default=None, serialization_alias="pagesRendered")
    pages_sent: int | None = Field(default=None, serialization_alias="pagesSent")
    pages_dropped: int | None = Field(default=None, serialization_alias="pagesDropped")


class RunAuditDocument(CamelModel):
    id: str
    document_type: str
    file_name: str | None = Field(default=None, serialization_alias="fileName")
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
    started_at: str | None = Field(default=None, serialization_alias="startedAt")
    finished_at: str | None = Field(default=None, serialization_alias="finishedAt")
    duration_ms: int = Field(default=0, serialization_alias="durationMs")
    extraction_ms: int = Field(default=0, serialization_alias="extractionMs")
    validation_ms: int = Field(default=0, serialization_alias="validationMs")
    validation_mode: str = Field(default="logic_only", serialization_alias="validationMode")
    validation_label: str = Field(default="", serialization_alias="validationLabel")
    llm_model: str | None = Field(default=None, serialization_alias="llmModel")


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
