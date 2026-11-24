from repody.app.execute import run_outcome
from repody.rules.evaluate import RuleOutcome, evaluate_rule
from repody.schemas.rule import Condition, FieldRef, LiteralValue, Rule, Severity

PASSING = evaluate_rule(
    Rule(id="r", conditions=[Condition(id="c", left=FieldRef(field="a"), operator="EXISTS")]),
    {"a": (1, "number")},
)


def test_a_run_with_every_document_read_and_no_failed_rule_passes():
    assert run_outcome([PASSING], extraction_complete=True) == "passed"


def test_a_run_where_nothing_was_read_needs_review():
    assert run_outcome([], extraction_complete=False) == "warning"
    assert run_outcome([PASSING], extraction_complete=False) == "warning"


def _unchecked(severity: Severity) -> RuleOutcome:
    """A rule whose field was not read: skipped."""
    rule = Rule(
        id="u",
        severity=severity,
        conditions=[
            Condition(
                id="c",
                left=FieldRef(field="total"),
                operator="==",
                right=LiteralValue(value="100"),
            )
        ],
    )
    outcome = evaluate_rule(rule, {"total": (None, "number")})
    assert outcome.status == "skipped"
    return outcome


def test_a_reject_rule_that_could_not_be_checked_needs_review():
    assert run_outcome([PASSING, _unchecked("reject")], extraction_complete=True) == "warning"


def test_a_flag_rule_that_could_not_be_checked_changes_nothing():
    assert run_outcome([PASSING, _unchecked("flag")], extraction_complete=True) == "passed"


def test_a_run_whose_second_read_did_not_confirm_every_field_needs_review():
    assert run_outcome([PASSING], extraction_complete=True, confirmed=False) == "warning"
    failed = evaluate_rule(
        Rule(id="f", conditions=[Condition(id="c", left=FieldRef(field="a"), operator="IS_EMPTY")]),
        {"a": (1, "number")},
    )
    assert run_outcome([failed], extraction_complete=True, confirmed=False) == "failed"
