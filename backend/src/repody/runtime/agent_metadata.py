"""Persist agent stage outcomes on run_metadata for durable handoff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from repody.agents.idp.contracts import (
    DocumentExtraction,
    ExtractedField,
    ExtractionOutput,
    IdpExtractionMeta,
    IdpOutcome,
    RuleResult,
    ValidationOutput,
)
from repody.app.run.helpers import meta_to_dict
from repody.infra.db.models import Run
from repody.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus

_AGENT_OUTCOMES_KEY = "agentOutcomes"
_PENDING_COMPLETION_KEY = "pendingCompletion"


@dataclass(frozen=True, slots=True)
class PendingCompletion:
    """Platform-owned deferred completion payload (finalized by services/run)."""

    overall_status: str
    summary_total: int
    summary_passed: int
    summary_failed: int
    fields_extracted: int
    run_metadata: dict[str, Any]
    progress: dict[str, Any] | None = None


def _meta(run: Run) -> dict[str, Any]:
    raw = run.run_metadata
    return dict(raw) if isinstance(raw, dict) else {}


def _str_field(raw: dict[str, Any], camel: str, snake: str, default: str = "") -> str:
    value = raw.get(camel)
    if value is None:
        value = raw.get(snake)
    return str(value) if value is not None else default


def _opt_str(raw: dict[str, Any], camel: str, snake: str) -> str | None:
    value = raw.get(camel)
    if value is None:
        value = raw.get(snake)
    return value if isinstance(value, str) else None


def _opt_int(raw: dict[str, Any], camel: str, snake: str) -> int | None:
    value = raw.get(camel)
    if value is None:
        value = raw.get(snake)
    return value if isinstance(value, int) else None


def _opt_dict(raw: dict[str, Any], camel: str, snake: str) -> dict[str, Any] | None:
    value = raw.get(camel)
    if value is None:
        value = raw.get(snake)
    return value if isinstance(value, dict) else None


def _bool_field(raw: dict[str, Any], camel: str, snake: str) -> bool:
    value = raw.get(camel)
    if value is None:
        value = raw.get(snake)
    return bool(value or False)


def _int_field(raw: dict[str, Any], camel: str, snake: str, default: int = 0) -> int:
    value = raw.get(camel)
    if value is None:
        value = raw.get(snake)
    return int(value or default)


def _extraction_meta_from_dict(raw: dict[str, Any]) -> IdpExtractionMeta:
    """Accept camelCase (canonical) or legacy snake_case keys."""
    return IdpExtractionMeta(
        read_path_config=_str_field(raw, "readPathConfig", "read_path_config"),
        read_path_used=_str_field(raw, "readPathUsed", "read_path_used"),
        validation_mode=_str_field(raw, "validationMode", "validation_mode"),
        document_model_id=_opt_str(raw, "documentModelId", "document_model_id"),
        extraction_ms=_int_field(raw, "extractionMs", "extraction_ms"),
        cache_hit=_bool_field(raw, "cacheHit", "cache_hit"),
        gpu_cold_start_likely=_bool_field(raw, "gpuColdStartLikely", "gpu_cold_start_likely"),
        fields_extracted=_int_field(raw, "fieldsExtracted", "fields_extracted"),
        markdown_extraction=_bool_field(raw, "markdownExtraction", "markdown_extraction"),
        markdown_text=_opt_str(raw, "markdownText", "markdown_text"),
        raw_text=_opt_str(raw, "rawText", "raw_text"),
        pages_rendered=_opt_int(raw, "pagesRendered", "pages_rendered"),
        pages_sent=_opt_int(raw, "pagesSent", "pages_sent"),
        pages_dropped=_opt_int(raw, "pagesDropped", "pages_dropped"),
        native_pdf=_opt_dict(raw, "nativePdf", "native_pdf"),
    )


def _extraction_to_dict(extraction: ExtractionOutput) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    for doc in extraction.by_document:
        documents.append(
            {
                "documentId": doc.document_id,
                "markdownText": doc.markdown_text,
                "rawText": doc.raw_text,
                "meta": meta_to_dict(doc.meta),
                "fields": [
                    {
                        "key": field.key,
                        "value": field.value,
                        "fieldType": field.field_type,
                        "extracted": field.extracted,
                        "confidence": field.confidence,
                        "description": field.description,
                    }
                    for field in doc.fields
                ],
            }
        )
    return {"byDocument": documents}


def _extraction_from_dict(raw: dict[str, Any]) -> ExtractionOutput:
    docs_raw = raw.get("byDocument")
    if not isinstance(docs_raw, list):
        docs_raw = []
    documents: list[DocumentExtraction] = []
    for item in docs_raw:
        if not isinstance(item, dict):
            continue
        meta_raw = item.get("meta")
        if not isinstance(meta_raw, dict):
            raise ValueError("IDP handoff extraction document missing meta")
        fields_raw = item.get("fields")
        if not isinstance(fields_raw, list):
            fields_raw = []
        fields: list[ExtractedField] = []
        for field in fields_raw:
            if not isinstance(field, dict):
                continue
            fields.append(
                ExtractedField(
                    key=str(field.get("key") or ""),
                    value=str(field.get("value") or ""),
                    field_type=str(field.get("fieldType") or "string"),
                    extracted=bool(field.get("extracted")),
                    confidence=field.get("confidence")
                    if isinstance(field.get("confidence"), (int, float))
                    else None,
                    description=str(field.get("description") or ""),
                )
            )
        documents.append(
            DocumentExtraction(
                document_id=str(item.get("documentId") or ""),
                fields=tuple(fields),
                markdown_text=item.get("markdownText")
                if isinstance(item.get("markdownText"), str)
                else None,
                meta=_extraction_meta_from_dict(meta_raw),
                raw_text=item.get("rawText") if isinstance(item.get("rawText"), str) else None,
            )
        )
    return ExtractionOutput(by_document=tuple(documents))


def _validation_to_dict(validation: ValidationOutput) -> dict[str, Any]:
    return {
        "overallStatus": validation.overall_status,
        "summaryPassed": validation.summary_passed,
        "summaryFailed": validation.summary_failed,
        "ruleResults": [
            {
                "ruleId": rule.rule_id,
                "name": rule.name,
                "status": rule.status,
                "severity": rule.severity,
                "detail": rule.detail,
                "affectedFields": list(rule.affected_fields),
                "kind": rule.kind,
                "scope": rule.scope,
                "expression": rule.expression,
                "expectedValue": rule.expected_value,
                "actualValue": rule.actual_value,
            }
            for rule in validation.rule_results
        ],
    }


def _validation_from_dict(raw: dict[str, Any]) -> ValidationOutput:
    rules_raw = raw.get("ruleResults")
    if not isinstance(rules_raw, list):
        rules_raw = []
    rules: list[RuleResult] = []
    for item in rules_raw:
        if not isinstance(item, dict):
            continue
        affected = item.get("affectedFields")
        rules.append(
            RuleResult(
                rule_id=str(item.get("ruleId") or ""),
                name=str(item.get("name") or ""),
                status=str(item.get("status") or ""),
                severity=str(item.get("severity") or ""),
                detail=str(item.get("detail") or ""),
                affected_fields=tuple(str(x) for x in affected)
                if isinstance(affected, list)
                else (),
                kind=str(item.get("kind") or "logic"),
                scope=str(item.get("scope") or "intra"),
                expression=str(item.get("expression") or ""),
                expected_value=item.get("expectedValue")
                if isinstance(item.get("expectedValue"), str)
                else None,
                actual_value=item.get("actualValue")
                if isinstance(item.get("actualValue"), str)
                else None,
            )
        )
    return ValidationOutput(
        rule_results=tuple(rules),
        overall_status=str(raw.get("overallStatus") or "passed"),
        summary_passed=int(raw.get("summaryPassed") or 0),
        summary_failed=int(raw.get("summaryFailed") or 0),
    )


def record_agent_outcome(run: Run, outcome: AgentOutcome) -> None:
    meta = _meta(run)
    outcomes = dict(meta.get(_AGENT_OUTCOMES_KEY) or {})
    payload: dict[str, Any] = {
        "status": outcome.status.value,
        "errorCount": len(outcome.errors),
    }
    if outcome.agent is AgentId.IDP and isinstance(outcome.payload, IdpOutcome):
        payload["workflowId"] = outcome.payload.workflow_id
        payload["extraction"] = _extraction_to_dict(outcome.payload.extraction)
        payload["validation"] = _validation_to_dict(outcome.payload.validation)
        # Keep short summary fields for operators / stale tooling.
        payload["overallStatus"] = outcome.payload.validation.overall_status
        payload["summaryPassed"] = outcome.payload.validation.summary_passed
        payload["summaryFailed"] = outcome.payload.validation.summary_failed
    else:
        payload["summary"] = getattr(outcome.payload, "summary", "") or ""
    outcomes[outcome.agent.value] = payload
    meta[_AGENT_OUTCOMES_KEY] = outcomes
    run.run_metadata = meta


def store_pending_completion(run: Run, outcome: PendingCompletion) -> None:
    meta = _meta(run)
    meta[_PENDING_COMPLETION_KEY] = {
        "overallStatus": outcome.overall_status,
        "summaryTotal": outcome.summary_total,
        "summaryPassed": outcome.summary_passed,
        "summaryFailed": outcome.summary_failed,
        "fieldsExtracted": outcome.fields_extracted,
        "runMetadata": outcome.run_metadata,
        "progress": outcome.progress,
    }
    run.run_metadata = meta


def pending_completion_from_run(run: Run) -> PendingCompletion | None:
    meta = _meta(run)
    raw = meta.get(_PENDING_COMPLETION_KEY)
    if not isinstance(raw, dict):
        return None
    meta_blob = raw.get("runMetadata")
    return PendingCompletion(
        overall_status=str(raw.get("overallStatus") or "passed"),
        summary_total=int(raw.get("summaryTotal") or 0),
        summary_passed=int(raw.get("summaryPassed") or 0),
        summary_failed=int(raw.get("summaryFailed") or 0),
        fields_extracted=int(raw.get("fieldsExtracted") or 0),
        run_metadata=dict(meta_blob) if isinstance(meta_blob, dict) else {},
        progress=raw.get("progress") if isinstance(raw.get("progress"), dict) else None,
    )


def clear_pending_completion(run: Run) -> None:
    meta = _meta(run)
    meta.pop(_PENDING_COMPLETION_KEY, None)
    run.run_metadata = meta


def idp_outcome_from_run(run: Run) -> IdpOutcome | None:
    meta = _meta(run)
    outcomes = meta.get(_AGENT_OUTCOMES_KEY) or {}
    row = outcomes.get(AgentId.IDP.value)
    if not isinstance(row, dict):
        return None
    extraction_raw = row.get("extraction")
    validation_raw = row.get("validation")
    if not isinstance(extraction_raw, dict) or not isinstance(validation_raw, dict):
        # Old lightweight rows (pre-handoff payload) cannot be reconstructed honestly.
        return None
    return IdpOutcome(
        run_id=run.id,
        workflow_id=str(row.get("workflowId") or run.workflow_id),
        extraction=_extraction_from_dict(extraction_raw),
        validation=_validation_from_dict(validation_raw),
    )


def agent_status_recorded(run: Run, agent: AgentId) -> AgentStatus | None:
    meta = _meta(run)
    outcomes = meta.get(_AGENT_OUTCOMES_KEY) or {}
    row = outcomes.get(agent.value)
    if not isinstance(row, dict):
        return None
    raw = row.get("status")
    if not raw:
        return None
    try:
        return AgentStatus(str(raw))
    except ValueError:
        return None
