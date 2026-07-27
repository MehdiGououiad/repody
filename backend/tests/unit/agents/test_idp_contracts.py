"""Unit tests for IDP contracts, planning, summarization, and mappers."""

from __future__ import annotations

from audit_workbench.agents.idp.adapters.mapping import (
    build_idp_input,
    document_spec_from_snapshot,
    rule_spec_from_dict,
    stored_document,
)
from audit_workbench.agents.idp.contracts import DocumentSpec, SchemaField
from audit_workbench.agents.idp.compose import build_extraction_plan, needs_extraction
from audit_workbench.agents.idp.adapters.validate import summarize_validation
from audit_workbench.agents.idp.contracts import RuleResult
from audit_workbench.agents.idp.run import agent_status_from_idp
from audit_workbench.platform.contracts.agent import AgentId, AgentOutcome, AgentStatus
from audit_workbench.platform.contracts.result import AppError, ErrorCode, Result
from audit_workbench.services.run.snapshot import SnapshotDocument, SnapshotSchemaField


def test_result_ok_and_fail():
    ok = Result.ok(42)
    assert ok.is_ok
    assert ok.unwrap() == 42
    none_ok = Result.ok(None)
    assert none_ok.is_ok
    assert none_ok.unwrap() is None
    err = Result.fail(AppError(code=ErrorCode.EXTRACTION, message="bad json"))
    assert not err.is_ok
    assert err.error is not None
    assert err.error.code is ErrorCode.EXTRACTION


def test_agent_outcome_envelope():
    outcome = AgentOutcome(
        agent=AgentId.IDP,
        status=AgentStatus.PASSED,
        payload={"run_id": "r1"},
        errors=(),
    )
    assert outcome.agent is AgentId.IDP
    assert outcome.status is AgentStatus.PASSED


def test_needs_extraction_requires_file_and_schema_or_markdown():
    spec = DocumentSpec(
        id="d1",
        label="Invoice",
        schema_fields=(SchemaField(name="total"),),
    )
    assert needs_extraction(spec, None) is False
    stored = stored_document(
        document_id="d1",
        storage_key="k1",
        mime_type="application/pdf",
    )
    assert needs_extraction(spec, stored) is True
    empty = DocumentSpec(id="d2", label="x", schema_fields=())
    assert needs_extraction(empty, stored) is False
    md = DocumentSpec(id="d3", label="x", schema_fields=(), markdown_extraction=True)
    assert needs_extraction(md, stored) is True


def test_build_extraction_plan():
    docs = (
        DocumentSpec(id="a", label="A", schema_fields=(SchemaField(name="x"),)),
        DocumentSpec(id="b", label="B", schema_fields=()),
    )
    stored = {
        "a": stored_document(document_id="a", storage_key="ka", mime_type="application/pdf"),
    }
    jobs = build_extraction_plan(docs, stored)
    assert len(jobs) == 1
    assert jobs[0].document_id == "a"


def test_summarize_validation_partial():
    results = (
        RuleResult(rule_id="1", name="ok", status="passed", severity="reject", detail="", affected_fields=()),
        RuleResult(rule_id="2", name="bad", status="failed", severity="warn", detail="", affected_fields=()),
    )
    out = summarize_validation(results)
    assert out.overall_status == "warning"
    assert out.summary_passed == 1
    assert out.summary_failed == 1


def test_agent_status_from_idp_outcome():
    from audit_workbench.agents.idp.contracts import ExtractionOutput
    from audit_workbench.agents.idp.contracts import IdpOutcome
    from audit_workbench.agents.idp.contracts import RuleResult

    results = (
        RuleResult(
            rule_id="r1",
            name="always",
            status="passed",
            severity="reject",
            detail="ok",
            affected_fields=(),
            kind="logic",
        ),
    )
    summary = summarize_validation(results)
    outcome = IdpOutcome(
        run_id="r",
        workflow_id="w",
        extraction=ExtractionOutput(by_document=()),
        validation=summary,
        errors=(),
    )
    assert agent_status_from_idp(outcome) in {
        AgentStatus.PASSED,
        AgentStatus.FAILED,
        AgentStatus.PARTIAL,
    }


def test_mappers_build_idp_input():
    snap = SnapshotDocument(
        id="doc-1",
        document_type="Invoice",
        position=0,
        extraction_mode="document_model",
        validation_mode="logic_only",
        document_model_id="repody:vlm",
        schema_fields=[
            SnapshotSchemaField(
                id="sf-1",
                name="total",
                description="Total TTC",
                position=0,
                template_type="number",
            )
        ],
    )
    spec = document_spec_from_snapshot(snap)
    assert spec.label == "Invoice"
    assert spec.schema_fields[0].name == "total"

    rule = rule_spec_from_dict(
        {
            "id": "r1",
            "name": "Total positive",
            "kind": "logic",
            "scope": "intra",
            "severity": "reject",
            "applies_to": ["total"],
            "body": "total > 0",
            "conditions": [],
        }
    )
    assert rule.kind == "logic"
    assert rule.applies_to == ("total",)

    inp = build_idp_input(
        run_id="run-1",
        workflow_id="wf-1",
        documents=[snap],
        rules=[{"id": "r1", "name": "r", "kind": "logic", "body": "true"}],
        stored=[
            stored_document(
                document_id="doc-1",
                storage_key="s3://x",
                mime_type="application/pdf",
                size_bytes=10,
            )
        ],
        workflow_name="Demo",
    )
    assert inp.run_id == "run-1"
    assert inp.workflow.workflow_name == "Demo"
    assert len(inp.documents) == 1
    assert len(inp.workflow.documents) == 1
    assert len(inp.workflow.rules) == 1
