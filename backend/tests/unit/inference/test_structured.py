from audit_workbench.inference.structured import (
    extract_json_object,
    openai_json_schema_format,
    parse_structured_response,
)
from audit_workbench.inference.structured_models import LlmRuleVerdict


def test_parse_structured_response_from_json_block():
    raw = 'Here is the result:\n{"passed": true, "detail": "OK"}'
    verdict = parse_structured_response(LlmRuleVerdict, raw)
    assert verdict.passed is True
    assert verdict.detail == "OK"


def test_openai_json_schema_format_for_llm_rules():
    fmt = openai_json_schema_format(LlmRuleVerdict, strict=True)
    assert fmt["json_schema"]["strict"] is True
    assert "passed" in fmt["json_schema"]["schema"]["properties"]


def test_extract_json_object_rejects_non_object():
    try:
        extract_json_object("[1,2,3]")
        raised = False
    except ValueError:
        raised = True
    assert raised
