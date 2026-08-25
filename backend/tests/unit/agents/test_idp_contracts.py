"""Unit tests for IDP contracts, planning, summarization, and mappers."""

from __future__ import annotations

import pytest

from repody.agents.idp.adapters.mapping import (
    build_idp_input,
    document_spec_from_snapshot,
    rule_dict_from_spec,
    rule_spec_from_dict,
    stored_document,
)
from repody.agents.idp.adapters.validate import summarize_validation, validate_extraction
from repody.agents.idp.compose import build_extraction_plan
from repody.agents.idp.contracts import (
    DocumentExtraction,
    DocumentSpec,
    ExtractedField,
    ExtractionOutput,
    IdpExtractionMeta,
    IdpOutcome,
    RuleResult,
    SchemaField,
)
from repody.agents.idp.run import agent_status_from_idp
from repody.app.run.snapshot import SnapshotDocument, SnapshotSchemaField
from repody.extraction.modes import LOGIC_VALIDATION, extraction_is_needed
from repody.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus
from repody.runtime.contracts.result import AppError, ErrorCode, Result


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


def test_extraction_is_needed_requires_file_and_schema_or_markdown():
    assert (
        extraction_is_needed(has_file=False, has_schema_fields=True, markdown_extraction=False)
        is False
    )
    assert (
        extraction_is_needed(has_file=True, has_schema_fields=True, markdown_extraction=False)
        is True
    )
    assert (
        extraction_is_needed(has_file=True, has_schema_fields=False, markdown_extraction=False)
        is False
    )
    assert (
        extraction_is_needed(has_file=True, has_schema_fields=False, markdown_extraction=True)
        is True
    )


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
        RuleResult(
            rule_id="1",
            name="ok",
            status="passed",
            severity="reject",
            detail="",
            affected_fields=(),
        ),
        RuleResult(
            rule_id="2", name="bad", status="failed", severity="warn", detail="", affected_fields=()
        ),
    )
    out = summarize_validation(results)
    assert out.overall_status == "warning"
    assert out.summary_passed == 1
    assert out.summary_failed == 1


def test_agent_status_from_idp_outcome():
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


def test_rule_spec_round_trip_preserves_junction():
    rule = rule_spec_from_dict(
        {
            "id": "r1",
            "name": "Total positive",
            "kind": "logic",
            "scope": "intra",
            "severity": "reject",
            "applies_to": ["total"],
            "body": "total > 0",
            "conditions": [
                {
                    "left": {"kind": "field", "value": "total"},
                    "operator": ">",
                    "right": {"kind": "literal", "value": "0"},
                }
            ],
            "condition_junction": "OR",
        }
    )
    assert rule.kind == "logic"
    assert rule.applies_to == ("total",)
    assert rule.condition_junction == "OR"
    assert len(rule.conditions) == 1

    as_dict = rule_dict_from_spec(rule)
    assert as_dict["condition_junction"] == "OR"
    assert as_dict["applies_to"] == ["total"]
    assert as_dict["body"] == "total > 0"
    assert as_dict["conditions"] == list(rule.conditions)


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

    inp = build_idp_input(
        run_id="run-1",
        workflow_id="wf-1",
        documents=[snap],
        rules=[
            {
                "id": "r1",
                "name": "r",
                "kind": "logic",
                "body": "true",
                "condition_junction": "AND",
            }
        ],
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
    assert inp.workflow.rules[0].condition_junction == "AND"


@pytest.mark.asyncio
async def test_validate_extraction_consumes_rule_spec():
    extraction = ExtractionOutput(
        by_document=(
            DocumentExtraction(
                document_id="doc-1",
                fields=(
                    ExtractedField(
                        key="total",
                        value="10",
                        field_type="number",
                        extracted=True,
                    ),
                ),
                markdown_text=None,
                meta=IdpExtractionMeta(
                    read_path_config="document_model",
                    read_path_used="document_model",
                    validation_mode="logic_only",
                    document_model_id="repody:vlm",
                    cache_hit=False,
                    extraction_ms=1,
                    fields_extracted=1,
                ),
            ),
        )
    )
    rules = (
        rule_spec_from_dict(
            {
                "id": "r1",
                "name": "Total positive",
                "kind": "logic",
                "scope": "intra",
                "severity": "reject",
                "applies_to": [],
                "body": "total > 0",
                "conditions": [],
            }
        ),
    )
    out = await validate_extraction(
        extraction,
        rules=rules,
        labels={"doc-1": "Invoice"},
        multi_document=False,
        validation_mode=LOGIC_VALIDATION,
    )
    assert out.summary_passed == 1
    assert out.overall_status == "passed"
    assert out.rule_results[0].rule_id == "r1"
