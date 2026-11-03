from repody.app.workflow.validation import (
    validate_rules_preview,
    validate_workflow_rule,
)
from repody.schemas.workflow import (
    WorkflowRuleSchema,
)


def test_llm_rules_are_rejected():
    rule = WorkflowRuleSchema(
        id="r1",
        name="Fee check",
        kind="llm",
        scope="intra",
        applies_to=["d1"],
        body="Compare @total with @missing_field",
        severity="flag",
    )
    assert validate_workflow_rule(rule) == ["Fee check: only logic rules are supported."]


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
    issues = validate_workflow_rule(rule)
    assert issues == ["Balance: Add at least one condition."]


def test_validate_logic_rule_rejects_body_without_conditions():
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
    issues = validate_workflow_rule(rule)
    assert issues == ["Balance: Add at least one condition."]


def test_validate_rules_preview_returns_per_rule_rows():
    condition = {
        "id": "c1",
        "left": {"kind": "field", "value": "total"},
        "operator": ">",
        "right": {"kind": "literal", "value": "0"},
    }
    rules = [
        WorkflowRuleSchema(
            id="r1",
            name="Ok",
            kind="logic",
            scope="intra",
            body="total > 0",
            conditions=[condition],
            condition_junction="AND",
            severity="flag",
        ),
        WorkflowRuleSchema(id="r2", name="Empty", kind="logic", scope="intra", conditions=[]),
    ]
    rows = validate_rules_preview(rules)
    assert [row.rule_id for row in rows] == ["r1", "r2"]
    assert rows[0].issues == []
    assert rows[1].issues == ["Empty: Add at least one condition."]
