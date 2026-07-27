"""Handoff metadata round-trip — real IdpOutcome fields, no hollow reconstruction."""

from __future__ import annotations

from types import SimpleNamespace

from audit_workbench.agents.idp.contracts import (
    DocumentExtraction,
    ExtractedField,
    ExtractionOutput,
    IdpOutcome,
    RuleResult,
    ValidationOutput,
)
from audit_workbench.extraction.types import ExtractionMetadata
from audit_workbench.platform.agent_metadata import idp_outcome_from_run, record_agent_outcome
from audit_workbench.platform.contracts.agent import AgentId, AgentOutcome, AgentStatus


def test_idp_outcome_round_trip_preserves_extraction_fields() -> None:
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
                    meta=ExtractionMetadata(
                        read_path_config="document_model",
                        read_path_used="document_model",
                        read_path_label="Document model",
                        validation_mode="logic",
                        validation_label="Logic",
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
    restored = idp_outcome_from_run(run)  # type: ignore[arg-type]
    assert restored is not None
    assert restored.workflow_id == "wf-1"
    assert len(restored.extraction.by_document) == 1
    doc = restored.extraction.by_document[0]
    assert doc.document_id == "doc-1"
    assert doc.fields[0].key == "invoice_number"
    assert doc.fields[0].value == "F-42"
    assert doc.fields[0].confidence == 0.91
    assert doc.markdown_text == "# Invoice"
    assert doc.meta.document_model_id == "repody:vlm"
    assert restored.validation.summary_passed == 1
    assert restored.validation.rule_results[0].rule_id == "r1"


def test_idp_outcome_from_run_rejects_incomplete_legacy_rows() -> None:
    run = SimpleNamespace(
        id="run-1",
        workflow_id="wf-1",
        run_metadata={
            "agentOutcomes": {
                "idp": {
                    "status": "passed",
                    "overallStatus": "passed",
                    "summaryPassed": 1,
                    "summaryFailed": 0,
                }
            }
        },
    )
    assert idp_outcome_from_run(run) is None  # type: ignore[arg-type]
