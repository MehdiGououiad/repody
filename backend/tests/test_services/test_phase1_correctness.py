from __future__ import annotations

import pytest

from audit_workbench.extraction.base import ExtractedFieldResult, ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.cache import (
    cache_key_from_storage,
    schema_fingerprint,
    should_cache_result,
)
from audit_workbench.extraction.document_modes import resolve_run_validation_mode
from audit_workbench.extraction.field_json import parse_fields_json
from audit_workbench.extraction.schema_fields import empty_fields_from_schema
from audit_workbench.rules.runner import skipped_llm_results


def test_empty_schema_fields_have_no_fake_values():
    schema = [SchemaFieldSpec(name="total_amount", description="Total TTC")]
    fields = empty_fields_from_schema(schema)
    assert len(fields) == 1
    assert fields[0].value == "—"
    assert fields[0].extracted is False


def test_parse_fields_json_uses_schema_names():
    schema = [
        SchemaFieldSpec(name="contract_id", description="Contract ID"),
        SchemaFieldSpec(name="annual_fee", description="Annual Fee"),
    ]
    raw = (
        '{"fields":['
        '{"name":"contract_id","value":"ABC-991","confidence":0.95},'
        '{"name":"annual_fee","value":"12 500,00","confidence":0.9}'
        "]}"
    )
    fields = parse_fields_json(raw, schema)
    by_key = {f.key: f for f in fields}
    assert by_key["contract_id"].extracted is True
    assert by_key["contract_id"].value == "ABC-991"
    assert by_key["annual_fee"].extracted is True
    assert by_key["annual_fee"].value == "12500.00"


def test_should_not_cache_empty_extractions():
    empty = ExtractionResult(
        fields=[
            ExtractedFieldResult(
                key="x", description="", value="—", type="string", confidence=None, extracted=False
            )
        ],
        raw_text="some text",
    )
    good = ExtractionResult(
        fields=[
            ExtractedFieldResult(
                key="x", description="", value="1", type="string", confidence=0.9, extracted=True
            )
        ],
        raw_text="some text",
    )
    assert should_cache_result(empty) is False
    assert should_cache_result(good) is True


def test_storage_cache_key_includes_content_hash():
    key_a = cache_key_from_storage(
        storage_key="runs/a/file.pdf",
        file_size=100,
        content_hash="abc123",
        schema_fp="schema1",
        extraction_mode="read:document_model:val:logic_only",
        ocr_model="repody:vlm",
        extractor="pipeline",
    )
    key_b = cache_key_from_storage(
        storage_key="runs/a/file.pdf",
        file_size=100,
        content_hash="def456",
        schema_fp="schema1",
        extraction_mode="read:document_model:val:logic_only",
        ocr_model="repody:vlm",
        extractor="pipeline",
    )
    assert key_a != key_b
    assert "abc123" in key_a
    assert "extract:v6s" in key_a


def test_schema_fingerprint_includes_descriptions():
    same_names = [
        SchemaFieldSpec(name="total_amount", description="Total TTC"),
        SchemaFieldSpec(name="invoice_number", description="Invoice reference"),
    ]
    renamed_prompt = [
        SchemaFieldSpec(name="total_amount", description="Montant total TTC incluant taxes"),
        SchemaFieldSpec(name="invoice_number", description="Invoice reference"),
    ]
    assert schema_fingerprint(same_names) != schema_fingerprint(renamed_prompt)


def test_schema_fingerprint_includes_template_type():
    as_text = [SchemaFieldSpec(name="total_amount", description="Total", template_type="verbatim-string")]
    as_number = [SchemaFieldSpec(name="total_amount", description="Total", template_type="number")]
    assert schema_fingerprint(as_text) != schema_fingerprint(as_number)


def test_schema_fingerprint_stable_for_identical_schema():
    schema = [
        SchemaFieldSpec(name="total_amount", description="Total TTC"),
        SchemaFieldSpec(name="invoice_number", description="Invoice reference"),
    ]
    assert schema_fingerprint(schema) == schema_fingerprint(list(schema))


def test_skipped_llm_rules_use_skipped_status():
    results = skipped_llm_results(
        [{"id": "r1", "name": "Fees", "kind": "llm", "severity": "flag", "body": "check"}]
    )
    assert len(results) == 1
    assert results[0].status == "skipped"


@pytest.mark.asyncio
async def test_llm_unavailable_is_skipped_in_stub_mode(monkeypatch):
    from audit_workbench.inference.factory import get_inference_client
    from audit_workbench.rules.llm_evaluator import evaluate_llm_rule
    from audit_workbench.settings import get_settings

    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "stub")
    get_settings.cache_clear()
    get_inference_client.cache_clear()

    status, detail = await evaluate_llm_rule("Check total", {"total_amount": "6000"})
    assert status == "skipped"
    assert "disabled" in detail.lower() or "skipped" in detail.lower()


@pytest.mark.asyncio
async def test_llm_unavailable_is_error_when_model_runner_down(monkeypatch):
    import httpx
    import respx

    from audit_workbench.inference.factory import get_inference_client
    from audit_workbench.rules.llm_evaluator import evaluate_llm_rule
    from audit_workbench.settings import get_settings

    base = "http://model-runner-down.test/v1"
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "docker_model_runner")
    monkeypatch.setenv("AUDIT_DOCKER_MODEL_RUNNER_BASE_URL", base)
    monkeypatch.setenv("AUDIT_LLM_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("AUDIT_VALIDATION_MODEL", "repody/validation:test")
    get_settings.cache_clear()
    get_inference_client.cache_clear()

    with respx.mock:
        respx.get(f"{base}/models").mock(return_value=httpx.Response(503))

        status, detail = await evaluate_llm_rule("Check total", {"total_amount": "6000"})
        assert status == "error"
        assert "unavailable" in detail.lower()

    get_inference_client.cache_clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_llm_rule_rejects_unknown_field_reference_before_inference():
    from audit_workbench.rules.llm_evaluator import evaluate_llm_rule

    status, detail = await evaluate_llm_rule(
        "Verify that @missing_total is positive.",
        {"total_amount": "6000"},
    )

    assert status == "error"
    assert "@missing_total" in detail


def test_llm_field_references_are_unique_and_affected():
    from audit_workbench.rules.llm_evaluator import referenced_fields
    from audit_workbench.rules.types import collect_affected_fields

    body = "Compare @invoice.total_amount with @invoice.tax and @invoice.total_amount."
    assert referenced_fields(body) == ["invoice.total_amount", "invoice.tax"]
    assert collect_affected_fields({"kind": "llm", "body": body}) == [
        "invoice.total_amount",
        "invoice.tax",
    ]


def test_llm_rule_forces_logic_and_llm_validation_mode(monkeypatch):
    from audit_workbench.settings import get_settings

    monkeypatch.setenv("AUDIT_LLM_VALIDATION_ENABLED", "true")
    get_settings.cache_clear()

    assert resolve_run_validation_mode([{"kind": "llm"}]) == "logic_and_llm"


@pytest.mark.asyncio
async def test_single_llm_rule_uses_single_rule_evaluator(monkeypatch):
    from audit_workbench.rules import llm_evaluator

    calls = []

    async def fake_evaluate(body, field_values, **kwargs):
        calls.append((body, field_values, kwargs))
        return "passed", "Validated by mock LLM."

    monkeypatch.setattr(llm_evaluator, "evaluate_llm_rule", fake_evaluate)

    result = await llm_evaluator.evaluate_llm_rules_batch(
        [
            {
                "id": "rule-1",
                "name": "Plausible total",
                "body": "Verify @total_amount.",
            }
        ],
        {"total_amount": "42", "supplier": "Example"},
    )

    assert result == {"rule-1": ("passed", "Validated by mock LLM.")}
    assert calls == [
        (
            "Verify @total_amount.",
            {"total_amount": "42", "supplier": "Example"},
            {"rule_name": "Plausible total", "llm_model": None},
        )
    ]


def test_structured_llm_auto_enabled_when_llm_validation_on(monkeypatch):
    from audit_workbench.settings import get_settings

    monkeypatch.setenv("AUDIT_LLM_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("AUDIT_STRUCTURED_LLM_ENABLED", "false")
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.structured_llm_enabled is True


@pytest.mark.asyncio
async def test_llm_validation_requires_dedicated_model(monkeypatch):
    from audit_workbench.rules.llm_evaluator import evaluate_llm_rule
    from audit_workbench.settings import get_settings

    monkeypatch.setenv("AUDIT_LLM_VALIDATION_ENABLED", "true")
    monkeypatch.delenv("AUDIT_VALIDATION_MODEL", raising=False)
    get_settings.cache_clear()

    status, detail = await evaluate_llm_rule(
        "Verify @total_amount is positive.",
        {"total_amount": "6000"},
    )
    assert status == "error"
    assert "AUDIT_VALIDATION_MODEL" in detail
    assert "Repody VLM" in detail


def test_resolve_llm_validation_model_never_falls_back_to_repody_vlm(monkeypatch):
    from audit_workbench.inference.validation_model import resolve_llm_validation_model
    from audit_workbench.settings import get_settings

    monkeypatch.setenv("AUDIT_REPODY_VLM_MODEL", "repody/repody-vlm:q4_k_m-16k")
    monkeypatch.delenv("AUDIT_VALIDATION_MODEL", raising=False)
    get_settings.cache_clear()

    model, error = resolve_llm_validation_model()
    assert model is None
    assert error is not None
    assert "Repody VLM" in error
