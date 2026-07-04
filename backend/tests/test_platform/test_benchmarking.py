from audit_workbench.benchmarking import compare_value, html_report, score_fields, score_rules


def test_compare_value_handles_locale_amounts():
    assert compare_value("6 000,00 DH", "6000.00", comparison="amount", tolerance="0.01")
    assert not compare_value("5999.00", "6000.00", comparison="amount", tolerance="0.01")


def test_scores_fields_and_rules():
    field_score = score_fields(
        {"total": {"value": "6,000.00", "extracted": True, "confidence": 0.9}},
        [{"name": "total", "expected": "6000", "comparison": "amount"}],
    )
    rule_score = score_rules(
        [{"id": "r1", "name": "Rule", "status": "passed"}],
        [{"id": "r1", "name": "Rule", "expectedStatus": "passed"}],
    )
    assert field_score["accuracy"] == 1.0
    assert rule_score["accuracy"] == 1.0


def test_html_report_is_self_contained():
    rendered = html_report(
        {
            "generatedAt": "2026-06-11T00:00:00+00:00",
            "profile": "quick",
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "fieldAccuracy": 1.0,
                "ruleAccuracy": 1.0,
            },
            "results": [
                {
                    "case": "text-layer",
                    "model": "document_model",
                    "phase": "first",
                    "status": "passed",
                    "passed": True,
                    "wallMs": 100,
                    "fieldAccuracy": 1.0,
                    "ruleAccuracy": 1.0,
                }
            ],
            "environment": {"platform": {"queueBackend": "taskiq"}},
        }
    )
    assert "<!doctype html>" in rendered
    assert "text-layer" in rendered
    assert "queueBackend" in rendered
