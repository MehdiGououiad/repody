import pytest

from audit_workbench.schemas.workflow import (
    DocumentDefSchema,
    SchemaFieldSchema,
    WorkflowRuleSchema,
)
from audit_workbench.services.workflow.validation import (
    resolve_document_field_tokens,
    validate_rules_preview,
    validate_workflow_rule,
)


def test_resolve_document_field_tokens_multi_document():
    documents = [
        DocumentDefSchema(
            id="d1",
            document_type="Invoice",
            schema_fields=[SchemaFieldSchema(id="f1", name="Total", description="")],
        ),
        DocumentDefSchema(
            id="d2",
            document_type="Contract",
            schema_fields=[SchemaFieldSchema(id="f2", name="Amount", description="")],
        ),
    ]
    tokens = resolve_document_field_tokens(documents, ["d1"])
    assert tokens == ["invoice.total"]


def test_validate_llm_rule_unknown_field_reference():
    documents = [
        DocumentDefSchema(
            id="d1",
            document_type="Invoice",
            schema_fields=[SchemaFieldSchema(id="f1", name="Total", description="")],
        )
    ]
    rule = WorkflowRuleSchema(
        id="r1",
        name="Fee check",
        kind="llm",
        scope="intra",
        applies_to=["d1"],
        body="Compare @total with @missing_field",
        severity="flag",
    )
    issues = validate_workflow_rule(rule, documents)
    assert any("missing_field" in issue for issue in issues)


def test_validate_logic_rule_requires_conditions():
    rule = WorkflowRuleSchema(
        id="r1",
        name="Balance",
        kind="logic",
        scope="intra",
        applies_to=["d1"],
        conditions=[],
        body="",
        severity="flag",
    )
    issues = validate_workflow_rule(rule, [])
    assert issues == ["Balance: Add at least one condition."]


def test_validate_logic_rule_rejects_body_without_conditions():
    documents = [
        DocumentDefSchema(
            id="d1",
            document_type="Invoice",
            schema_fields=[SchemaFieldSchema(id="f1", name="Total", description="")],
        )
    ]
    rule = WorkflowRuleSchema(
        id="r1",
        name="Balance",
        kind="logic",
        scope="intra",
        applies_to=["d1"],
        conditions=[],
        body="total_amount > 0",
        severity="flag",
    )
    issues = validate_workflow_rule(rule, documents)
    assert issues == ["Balance: Add at least one condition."]


def test_validate_rules_preview_returns_per_rule_rows():
    documents = [
        DocumentDefSchema(
            id="d1",
            document_type="Invoice",
            schema_fields=[SchemaFieldSchema(id="f1", name="Total", description="")],
        )
    ]
    rules = [
        WorkflowRuleSchema(
            id="r1",
            name="Ok",
            kind="llm",
            scope="intra",
            applies_to=["d1"],
            body="Check @total",
            severity="flag",
        ),
        WorkflowRuleSchema(
            id="r2",
            name="Empty",
            kind="llm",
            scope="intra",
            applies_to=["d1"],
            body="",
            severity="flag",
        ),
    ]
    rows = validate_rules_preview(documents, rules)
    assert rows[0]["issues"] == []
    assert rows[1]["issues"] == ["LLM prompt is empty."]
