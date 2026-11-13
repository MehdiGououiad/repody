from repody.app.execute import run_outcome
from repody.rules.evaluate import evaluate_rule
from repody.schemas.rule import Condition, FieldRef, Rule

PASSING = evaluate_rule(
    Rule(id="r", conditions=[Condition(id="c", left=FieldRef(field="a"), operator="EXISTS")]),
    {"a": (1, "number")},
)


def test_a_run_with_every_document_read_and_no_failed_rule_passes():
    assert run_outcome([PASSING], extraction_complete=True) == "passed"


def test_a_run_where_nothing_was_read_needs_review():
    assert run_outcome([], extraction_complete=False) == "warning"
    assert run_outcome([PASSING], extraction_complete=False) == "warning"
