"""Persist agent stage outcomes on run_metadata for durable handoff."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from audit_workbench.agents.fraud.contracts import FraudOutcome
from audit_workbench.agents.idp.contracts import (
    DocumentExtraction,
    ExtractedField,
    ExtractionOutput,
    IdpOutcome,
    RuleResult,
    ValidationOutput,
)
from audit_workbench.infra.db.models import Run
from audit_workbench.extraction.types import ExtractionMetadata
from audit_workbench.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus


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


def _extraction_meta_to_dict(meta: ExtractionMetadata) -> dict[str, Any]:
    return asdict(meta)


def _extraction_meta_from_dict(raw: dict[str, Any]) -> ExtractionMetadata:
    return ExtractionMetadata(
        read_path_config=str(raw.get("read_path_config") or ""),
        read_path_used=str(raw.get("read_path_used") or ""),
        read_path_label=str(raw.get("read_path_label") or ""),
        validation_mode=str(raw.get("validation_mode") or ""),
        validation_label=str(raw.get("validation_label") or ""),
        document_model_id=raw.get("document_model_id"),
        extraction_ms=int(raw.get("extraction_ms") or 0),
        cache_hit=bool(raw.get("cache_hit") or False),
        gpu_cold_start_likely=bool(raw.get("gpu_cold_start_likely") or False),
        fields_extracted=int(raw.get("fields_extracted") or 0),
        markdown_extraction=bool(raw.get("markdown_extraction") or False),
        markdown_text=raw.get("markdown_text") if isinstance(raw.get("markdown_text"), str) else None,
        raw_text=raw.get("raw_text") if isinstance(raw.get("raw_text"), str) else None,
        pages_rendered=raw.get("pages_rendered") if isinstance(raw.get("pages_rendered"), int) else None,
        pages_sent=raw.get("pages_sent") if isinstance(raw.get("pages_sent"), int) else None,
        pages_dropped=raw.get("pages_dropped") if isinstance(raw.get("pages_dropped"), int) else None,
    )


def _extraction_to_dict(extraction: ExtractionOutput) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    for doc in extraction.by_document:
        documents.append(
            {
                "documentId": doc.document_id,
                "markdownText": doc.markdown_text,
                "rawText": doc.raw_text,
                "meta": _extraction_meta_to_dict(doc.meta),
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
                affected_fields=tuple(str(x) for x in affected) if isinstance(affected, list) else (),
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
    elif outcome.agent is AgentId.FRAUD and isinstance(outcome.payload, FraudOutcome):
        payload["summary"] = outcome.payload.summary
        payload["signals"] = list(outcome.payload.signals)
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


def fraud_outcome_from_run(run: Run) -> FraudOutcome | None:
    meta = _meta(run)
    outcomes = meta.get(_AGENT_OUTCOMES_KEY) or {}
    row = outcomes.get(AgentId.FRAUD.value)
    if not isinstance(row, dict):
        return None
    signals_raw = row.get("signals")
    signals = tuple(str(s) for s in signals_raw) if isinstance(signals_raw, list) else ()
    return FraudOutcome(
        run_id=run.id,
        summary=str(row.get("summary") or ""),
        signals=signals,
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
