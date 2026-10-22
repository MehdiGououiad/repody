"""Persist agent stage outcomes on run_metadata."""

from __future__ import annotations

from typing import Any

from repody.agents.idp.contracts import (
    ExtractionOutput,
    IdpOutcome,
    ValidationOutput,
)
from repody.app.run.helpers import meta_to_dict
from repody.infra.db.models import Run
from repody.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus

_AGENT_OUTCOMES_KEY = "agentOutcomes"


def _meta(run: Run) -> dict[str, Any]:
    raw = run.run_metadata
    return dict(raw) if isinstance(raw, dict) else {}


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
