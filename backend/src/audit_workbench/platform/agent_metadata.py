"""Persist lightweight agent stage outcomes on run_metadata for handoff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from audit_workbench.agents.fraud.contracts import FraudOutcome
from audit_workbench.agents.idp.contracts import ExtractionOutput, IdpOutcome, ValidationOutput
from audit_workbench.db.models import Run
from audit_workbench.platform.contracts.agent import AgentId, AgentOutcome, AgentStatus


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


def record_agent_outcome(run: Run, outcome: AgentOutcome) -> None:
    meta = _meta(run)
    outcomes = dict(meta.get(_AGENT_OUTCOMES_KEY) or {})
    payload: dict[str, Any] = {
        "status": outcome.status.value,
        "errorCount": len(outcome.errors),
    }
    if outcome.agent is AgentId.IDP and isinstance(outcome.payload, IdpOutcome):
        payload["overallStatus"] = outcome.payload.validation.overall_status
        payload["summaryPassed"] = outcome.payload.validation.summary_passed
        payload["summaryFailed"] = outcome.payload.validation.summary_failed
        payload["workflowId"] = outcome.payload.workflow_id
    elif outcome.agent is AgentId.FRAUD and isinstance(outcome.payload, FraudOutcome):
        payload["summary"] = outcome.payload.summary
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
    overall = str(row.get("overallStatus") or "passed")
    return IdpOutcome(
        run_id=run.id,
        workflow_id=str(row.get("workflowId") or run.workflow_id),
        extraction=ExtractionOutput(by_document=()),
        validation=ValidationOutput(
            rule_results=(),
            overall_status=overall,
            summary_passed=int(row.get("summaryPassed") or 0),
            summary_failed=int(row.get("summaryFailed") or 0),
        ),
    )


def fraud_outcome_from_run(run: Run) -> FraudOutcome | None:
    meta = _meta(run)
    outcomes = meta.get(_AGENT_OUTCOMES_KEY) or {}
    row = outcomes.get(AgentId.FRAUD.value)
    if not isinstance(row, dict):
        return None
    return FraudOutcome(
        run_id=run.id,
        summary=str(row.get("summary") or ""),
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
