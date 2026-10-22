"""agentOutcomes is written for operators and read back only as a status."""

from __future__ import annotations

from types import SimpleNamespace

from repody.agents.idp.contracts import (
    DocumentExtraction,
    ExtractedField,
    ExtractionOutput,
    IdpExtractionMeta,
    IdpOutcome,
    RuleResult,
    ValidationOutput,
)
from repody.runtime.agent_metadata import agent_status_recorded, record_agent_outcome
from repody.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus


def test_record_agent_outcome_stores_status_and_extraction() -> None:
    outcome = IdpOutcome(
        run_id="run-1",
        workflow_id="wf-1",
        extraction=ExtractionOutput(
            by_document=(
                DocumentExtraction(
                    document_id="doc-1",
                    fields=(
                        ExtractedField(
                            key="invoice_number",
                            value="F-42",
                            field_type="string",
                            extracted=True,
                            confidence=0.91,
                            description="Invoice #",
                        ),
                    ),
                    markdown_text="# Invoice",
                    meta=IdpExtractionMeta(
                        read_path_config="document_model",
                        read_path_used="document_model",
                        validation_mode="logic",
                        document_model_id="repody:vlm",
                        fields_extracted=1,
                    ),
                    raw_text=None,
                ),
            )
        ),
        validation=ValidationOutput(
            rule_results=(
                RuleResult(
                    rule_id="r1",
                    name="Has invoice",
                    status="passed",
                    severity="error",
                    detail="ok",
                    affected_fields=("invoice_number",),
                ),
            ),
            overall_status="passed",
            summary_passed=1,
            summary_failed=0,
        ),
    )
    run = SimpleNamespace(id="run-1", workflow_id="wf-1", run_metadata=None)
    record_agent_outcome(
        run,  # type: ignore[arg-type]
        AgentOutcome(agent=AgentId.IDP, status=AgentStatus.PASSED, payload=outcome),
    )
    row = run.run_metadata["agentOutcomes"]["idp"]
    assert row["status"] == "passed"
    assert row["workflowId"] == "wf-1"
    assert row["extraction"]["byDocument"][0]["fields"][0]["key"] == "invoice_number"
    assert row["validation"]["summaryPassed"] == 1
    assert agent_status_recorded(run, AgentId.IDP) is AgentStatus.PASSED  # type: ignore[arg-type]


def test_agent_status_recorded_reads_lightweight_rows() -> None:
    run = SimpleNamespace(
        id="run-1",
        workflow_id="wf-1",
        run_metadata={"agentOutcomes": {"idp": {"status": "passed"}}},
    )
    assert agent_status_recorded(run, AgentId.IDP) is AgentStatus.PASSED  # type: ignore[arg-type]
