"""Map run snapshot / rule dicts / extraction types → IDP contracts.

Adapters may import snapshot helpers and extraction base types. Pure slices must not.
"""

from __future__ import annotations

from dataclasses import replace

from repody.agents.idp.contracts import (
    DocumentExtraction,
    DocumentSpec,
    ExtractedField,
    IdpExtractionMeta,
    IdpInput,
    IdpWorkflowConfig,
    RuleResult,
    RuleSpec,
    SchemaField,
    StoredDocument,
)
from repody.app.run.snapshot import SnapshotDocument, SnapshotSchemaField
from repody.catalog.registry import is_markdown_only_model
from repody.extraction.schema import (
    enum_values_from_row,
    iter_child_rows,
    merge_field_row,
)
from repody.extraction.types import ExtractedFieldResult, ExtractionMetadata, ExtractionResult
from repody.rules.types import RuleEvalResult


def _schema_field_from_row(row: dict) -> SchemaField | None:
    name = str(row.get("name") or "").strip()
    if not name:
        return None
    enum_raw = enum_values_from_row(row) or []
    children: list[SchemaField] = []
    raw_children = row.get("children")
    if isinstance(raw_children, list):
        for child_row in iter_child_rows(raw_children):
            child = _schema_field_from_row(child_row)
            if child is not None:
                children.append(child)
    return SchemaField(
        name=name,
        description=str(row.get("description") or ""),
        template_type=row.get("template_type"),
        enum_values=tuple(enum_raw),
        children=tuple(children),
    )


def schema_field_from_snapshot(field: SnapshotSchemaField) -> SchemaField:
    row = merge_field_row(
        field.name,
        field.description or "",
        field.template_type,
        field.field_config,
    )
    mapped = _schema_field_from_row(row)
    if mapped is None:
        return SchemaField(name=field.name, description=field.description or "")
    return mapped


def document_spec_from_snapshot(doc: SnapshotDocument) -> DocumentSpec:
    model_id = doc.document_model_id or "repody:vlm"
    markdown = bool(doc.markdown_extraction) or is_markdown_only_model(model_id)
    return DocumentSpec(
        id=doc.id,
        label=doc.document_type or doc.id,
        schema_fields=tuple(schema_field_from_snapshot(f) for f in doc.schema_fields),
        extraction_instructions=doc.extraction_instructions or "",
        markdown_extraction=markdown,
        native_pdf_auto=bool(getattr(doc, "native_pdf_auto", False)),
        document_model_id=model_id,
        extraction_mode=doc.extraction_mode or "document_model",
        position=doc.position,
    )


def rule_spec_from_dict(rule: dict) -> RuleSpec:
    applies = rule.get("applies_to") or []
    if not isinstance(applies, list):
        applies = []
    conditions = rule.get("conditions") or []
    if not isinstance(conditions, list):
        conditions = []
    junction = rule.get("condition_junction")
    return RuleSpec(
        id=str(rule.get("id") or ""),
        name=str(rule.get("name") or "Rule"),
        kind=str(rule.get("kind") or "logic").lower(),
        scope=str(rule.get("scope") or "intra").lower(),
        severity=str(rule.get("severity") or "reject"),
        applies_to=tuple(str(a) for a in applies),
        conditions=tuple(c for c in conditions if isinstance(c, dict)),
        body=str(rule.get("body") or ""),
        condition_junction=str(junction) if junction is not None else None,
    )


def rule_dict_from_spec(rule: RuleSpec) -> dict:
    """RuleSpec → rules-engine dict (single seam out of the IDP contract)."""
    return {
        "id": rule.id,
        "name": rule.name,
        "kind": rule.kind,
        "scope": rule.scope,
        "severity": rule.severity,
        "applies_to": list(rule.applies_to),
        "conditions": list(rule.conditions),
        "body": rule.body,
        "condition_junction": rule.condition_junction,
    }


def workflow_config_from_snapshot(
    *,
    workflow_id: str,
    documents: list[SnapshotDocument],
    rules: list[dict],
    workflow_name: str | None = None,
) -> IdpWorkflowConfig:
    return IdpWorkflowConfig(
        workflow_id=workflow_id,
        documents=tuple(document_spec_from_snapshot(d) for d in documents),
        rules=tuple(rule_spec_from_dict(r) for r in rules),
        workflow_name=workflow_name,
    )


def stored_document(
    *,
    document_id: str,
    storage_key: str,
    mime_type: str,
    size_bytes: int = 0,
) -> StoredDocument:
    return StoredDocument(
        document_id=document_id,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )


def build_idp_input(
    *,
    run_id: str,
    workflow_id: str,
    documents: list[SnapshotDocument],
    rules: list[dict],
    stored: list[StoredDocument],
    workflow_name: str | None = None,
) -> IdpInput:
    return IdpInput(
        run_id=run_id,
        workflow=workflow_config_from_snapshot(
            workflow_id=workflow_id,
            documents=documents,
            rules=rules,
            workflow_name=workflow_name,
        ),
        documents=tuple(stored),
    )


def extracted_field_from_result(row: ExtractedFieldResult) -> ExtractedField:
    return ExtractedField(
        key=row.key,
        value=row.value,
        field_type=row.type,
        extracted=row.extracted,
        confidence=row.confidence,
        description=row.description or "",
    )


def idp_meta_from_extraction(meta: ExtractionMetadata) -> IdpExtractionMeta:
    """Map pipeline ExtractionMetadata → IDP contract (labels stay at HTTP edge)."""
    return IdpExtractionMeta(
        read_path_config=meta.read_path_config,
        read_path_used=meta.read_path_used,
        validation_mode=meta.validation_mode,
        document_model_id=meta.document_model_id,
        extraction_ms=meta.extraction_ms,
        cache_hit=meta.cache_hit,
        gpu_cold_start_likely=meta.gpu_cold_start_likely,
        fields_extracted=meta.fields_extracted,
        markdown_extraction=meta.markdown_extraction,
        markdown_text=meta.markdown_text,
        raw_text=meta.raw_text,
        pages_rendered=meta.pages_rendered,
        pages_sent=meta.pages_sent,
        pages_dropped=meta.pages_dropped,
        native_pdf=getattr(meta, "native_pdf", None),
    )


def document_extraction_from_result(
    *,
    document_id: str,
    result: ExtractionResult,
    model_id: str = "repody:vlm",
) -> DocumentExtraction:
    if result.meta is None:
        raise ValueError("ExtractionResult.meta is required before IDP mapping")
    meta = result.meta
    if not meta.document_model_id:
        meta = replace(meta, document_model_id=model_id)
    idp_meta = idp_meta_from_extraction(meta)
    return DocumentExtraction(
        document_id=document_id,
        fields=tuple(extracted_field_from_result(f) for f in result.fields),
        markdown_text=result.markdown_text
        if result.markdown_text is not None
        else meta.markdown_text,
        raw_text=result.raw_text if result.raw_text is not None else meta.raw_text,
        meta=idp_meta,
    )


def rule_result_from_eval(row: RuleEvalResult) -> RuleResult:
    return RuleResult(
        rule_id=row.id,
        name=row.name,
        status=row.status,
        severity=row.severity,
        detail=row.detail,
        affected_fields=tuple(row.affected_fields or []),
        kind=row.kind,
        scope=row.scope,
        expression=row.expression or "",
        expected_value=row.expected_value,
        actual_value=row.actual_value,
    )
