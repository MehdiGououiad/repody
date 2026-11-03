"""NuExtract pipeline on a two-page bank statement: scalars, lists, enums, object arrays."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from tests.fixtures.bank_statement import (
    debit_list_schema,
    full_schema,
    get_bank_statement_ground_truth,
    list_fields_schema,
    load_bank_statement_bytes,
    load_bank_statement_text,
    model_payload,
    parse_bank_statement,
    summary_schema,
    transactions_schema,
)
from tests.fixtures.extraction_assertions import (
    assert_balance_identity,
    assert_currency_scalar,
    assert_date_list,
    assert_date_scalar,
    assert_enum_scalar,
    assert_integer_scalar,
    assert_is_json_list,
    assert_list_not_scalar,
    assert_multi_enum,
    assert_number_list,
    assert_number_scalar,
    assert_object_array_transactions,
    assert_verbatim_contains,
    assert_verbatim_string_list,
    field_map,
    require_field,
)
from tests.llm_mocks import disable_dmr_mock, enable_dmr_mock

from repody.catalog.registry import parse_document_model
from repody.extraction.branding import REPODY_VLM_CATALOG_ID
from repody.extraction.fields import fields_from_nuextract_json
from repody.extraction.nuextract import build_nuextract_template
from repody.extraction.pipeline import extract_document
from repody.extraction.render import prepare_nuextract_pages
from repody.extraction.types import ExtractedFieldResult, SchemaFieldSpec, load_document_bundle
from repody.extraction.vlm import extract_with_repody_vlm
from repody.rules.amounts import normalize_amount, parse_numeric_value
from repody.rules.value_coercion import MISSING
from repody.settings import get_settings

LIVE_LIST_LEN_TOLERANCE = 1
LIVE_SUM_TOLERANCE = 100.0
LIVE_ROW_TOLERANCE = 2
LIVE_SCALAR_TOLERANCE = 1.0
ALL_CATEGORIES = {"DEPOSIT", "WITHDRAWAL", "CARD", "FEE", "TRANSFER"}


@pytest.fixture
def ground_truth():
    return get_bank_statement_ground_truth()


@pytest.fixture
def disable_extraction_cache(monkeypatch):
    monkeypatch.setenv("AUDIT_EXTRACTION_CACHE_ENABLED", "false")
    get_settings.cache_clear()
    monkeypatch.setattr("repody.extraction.pipeline.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr("repody.extraction.pipeline.set_cached", AsyncMock())


def test_ground_truth_matches_statement_footer():
    gt = parse_bank_statement(*load_bank_statement_text())
    assert gt.page_count == 2
    assert gt.account_holder == "SARA EXEMPLE"
    assert gt.account_number == "0001234567890123"
    assert gt.agency == "CASA ANFA"
    assert gt.opening_balance == 48_250.00
    assert gt.closing_balance == 48_805.60
    assert gt.total_debit_movements == 29_944.40
    assert gt.total_credit_movements == 30_500.00
    assert (gt.debit_count, gt.credit_count, len(gt.movements)) == (38, 2, 40)
    assert set(gt.categories) == ALL_CATEGORIES
    assert_balance_identity(
        gt.opening_balance,
        gt.closing_balance,
        gt.total_debit_movements,
        gt.total_credit_movements,
    )


def test_pdf_renders_two_png_pages(ground_truth):
    bundle = load_document_bundle(
        load_bank_statement_bytes(), "application/pdf", settings=get_settings()
    )
    pages, rendered = prepare_nuextract_pages(bundle)
    assert rendered == ground_truth.page_count == 2
    assert len(pages) == 2
    assert all(mime == "image/png" for _, mime in pages)
    assert all(len(raw) > 500 for raw, _ in pages)


def test_full_template_covers_scalar_list_and_object_array():
    template = build_nuextract_template(full_schema())
    categories = ["DEPOSIT", "TRANSFER", "WITHDRAWAL", "CARD", "FEE", "OTHER"]
    assert template["opening_balance"] == "number"
    assert template["debit_transaction_count"] == "integer"
    assert template["opening_balance_date"] == "date"
    assert template["currency"] == "currency"
    assert template["currency_code"] == ["MAD", "EUR", "USD"]
    assert template["transaction_debit_amounts"] == ["number"]
    assert template["operation_dates"] == ["date"]
    assert template["transaction_descriptions"] == ["verbatim-string"]
    assert template["movement_categories"] == [categories]
    row = template["transactions"][0]
    assert row["operation_date"] == "date"
    assert row["value_date"] == "date"
    assert row["category"] == categories


@pytest.mark.parametrize(
    ("schema_factory", "field_name", "expected_template"),
    [
        (summary_schema, "opening_balance", "number"),
        (summary_schema, "debit_transaction_count", "integer"),
        (summary_schema, "opening_balance_date", "date"),
        (summary_schema, "currency", "currency"),
        (debit_list_schema, "transaction_debit_amounts", ["number"]),
        (list_fields_schema, "operation_dates", ["date"]),
        (list_fields_schema, "transaction_descriptions", ["verbatim-string"]),
    ],
)
def test_schema_template_types(schema_factory, field_name, expected_template):
    assert build_nuextract_template(schema_factory())[field_name] == expected_template


def _parse_golden_fields(schema: list[SchemaFieldSpec]) -> list[ExtractedFieldResult]:
    return fields_from_nuextract_json(json.dumps(model_payload(schema)), schema)


def assert_summary_fields(fields: list[ExtractedFieldResult], gt) -> None:
    assert_verbatim_contains(require_field(fields, "account_holder"), "SARA", "EXEMPLE")
    assert_verbatim_contains(require_field(fields, "agency"), "CASA", "ANFA")
    assert_number_scalar(require_field(fields, "opening_balance"), gt.opening_balance)
    assert_number_scalar(require_field(fields, "closing_balance"), gt.closing_balance)
    assert_number_scalar(require_field(fields, "total_debit_movements"), gt.total_debit_movements)
    assert_number_scalar(require_field(fields, "total_credit_movements"), gt.total_credit_movements)
    assert_integer_scalar(require_field(fields, "debit_transaction_count"), gt.debit_count)
    assert_integer_scalar(require_field(fields, "credit_transaction_count"), gt.credit_count)
    assert_date_scalar(require_field(fields, "opening_balance_date"), gt.opening_balance_iso)
    assert_date_scalar(require_field(fields, "closing_balance_date"), gt.closing_balance_iso)
    assert_currency_scalar(require_field(fields, "currency"), "MAD", "DIRHAM")
    assert_enum_scalar(require_field(fields, "currency_code"), {"MAD", "EUR", "USD"})
    assert require_field(fields, "account_number").value == gt.account_number


def assert_list_fields(fields: list[ExtractedFieldResult], gt) -> None:
    debits = assert_number_list(
        require_field(fields, "transaction_debit_amounts"),
        expected_len=gt.debit_count,
        expected_sum=gt.total_debit_movements,
    )
    credits = assert_number_list(
        require_field(fields, "transaction_credit_amounts"),
        expected_len=gt.credit_count,
        expected_sum=gt.total_credit_movements,
    )
    dates = assert_date_list(require_field(fields, "operation_dates"), expected_len=40)
    descriptions = assert_verbatim_string_list(
        require_field(fields, "transaction_descriptions"),
        expected_len=40,
        must_include=("VERSEMENT", "RETRAIT CARTE", "PAIEMENT PAR CARTE"),
    )
    assert_multi_enum(require_field(fields, "movement_categories"), ALL_CATEGORIES)
    assert debits[0] == gt.debit_amounts[0]
    assert debits[-1] == gt.debit_amounts[-1]
    assert credits == [12_000.0, 18_500.0]
    assert dates[0] in {gt.operation_dates_iso[0], "01/03", "01/03/2025"}
    assert "RETRAIT PAR CHEQUE" in descriptions[5].upper()
    assert "VERSEMENT" in descriptions[6].upper()


def assert_transactions_field(fields: list[ExtractedFieldResult], gt) -> None:
    rows = assert_object_array_transactions(require_field(fields, "transactions"), gt)
    assert parse_numeric_value(str(rows[0].get("debit_amount"))) == gt.debit_amounts[0]
    credit_row = next(r for r in rows if r.get("credit_amount") not in (None, "", MISSING, "null"))
    assert parse_numeric_value(str(credit_row.get("credit_amount"))) == 12_000.0


def test_golden_summary_scalar_types(ground_truth):
    assert_summary_fields(_parse_golden_fields(summary_schema()), ground_truth)


def test_golden_list_field_types(ground_truth):
    assert_list_fields(_parse_golden_fields(list_fields_schema()), ground_truth)


def test_golden_object_array_nested_types(ground_truth):
    assert_transactions_field(_parse_golden_fields(transactions_schema()), ground_truth)


@pytest.mark.parametrize(
    ("bad_json", "field_name"),
    [
        ('{"transaction_debit_amounts": 29944.40}', "transaction_debit_amounts"),
        ('{"transaction_debit_amounts": "29944.40"}', "transaction_debit_amounts"),
        ('{"operation_dates": "2025-03-01"}', "operation_dates"),
        ('{"transactions": {"operation_date": "2025-03-01"}}', "transactions"),
    ],
)
def test_rejects_wrong_json_shapes_for_list_and_object_fields(bad_json, field_name):
    field = field_map(fields_from_nuextract_json(bad_json, full_schema()))[field_name]
    if field_name == "transactions":
        assert not isinstance(json.loads(field.value), list)
        return
    with pytest.raises((json.JSONDecodeError, AssertionError)):
        assert_is_json_list(field.value, field_name=field_name)


def _inference_side_effect(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode())
    template_raw = (payload.get("chat_template_kwargs") or {}).get("template")
    if not template_raw:
        return httpx.Response(500, json={"error": "missing template"})
    registry = {field.name: field for field in full_schema()}
    schema = [registry.get(name, SchemaFieldSpec(name=name)) for name in json.loads(template_raw)]
    content = json.dumps(model_payload(schema))
    return httpx.Response(
        200, json={"choices": [{"message": {"role": "assistant", "content": content}}]}
    )


@pytest.fixture
def statement_model_router(monkeypatch):
    base = "http://statement-extract-mock.test/v1"
    router = enable_dmr_mock(monkeypatch, base=base)
    router.post(f"{base}/chat/completions").mock(side_effect=_inference_side_effect)
    yield router
    disable_dmr_mock(router)


@pytest.mark.asyncio
async def test_pipeline_mocked_full_schema_all_types(
    statement_model_router, ground_truth, disable_extraction_cache
):
    result = await extract_document(
        load_bank_statement_bytes(),
        "application/pdf",
        "Bank statement",
        full_schema(),
        extraction_mode="document_model",
        document_model_id=REPODY_VLM_CATALOG_ID,
        extraction_instructions="Bank statement: extract all fields exactly.",
    )
    assert result.meta is not None
    assert (result.meta.pages_rendered, result.meta.pages_sent, result.meta.pages_dropped) == (
        2,
        2,
        0,
    )
    assert_summary_fields(result.fields, ground_truth)
    assert_list_fields(result.fields, ground_truth)
    assert_transactions_field(result.fields, ground_truth)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "schema_factory",
    [summary_schema, list_fields_schema, transactions_schema, debit_list_schema],
)
async def test_pipeline_mocked_per_schema(
    schema_factory, statement_model_router, ground_truth, disable_extraction_cache
):
    result = await extract_document(
        load_bank_statement_bytes(),
        "application/pdf",
        "Bank statement",
        schema_factory(),
        extraction_mode="document_model",
        document_model_id=REPODY_VLM_CATALOG_ID,
    )
    assert result.meta is not None
    assert result.meta.pages_sent == 2
    if schema_factory is summary_schema:
        assert_summary_fields(result.fields, ground_truth)
    elif schema_factory is list_fields_schema:
        assert_list_fields(result.fields, ground_truth)
    elif schema_factory is transactions_schema:
        assert_transactions_field(result.fields, ground_truth)
    else:
        assert_number_list(
            require_field(result.fields, "transaction_debit_amounts"),
            expected_len=ground_truth.debit_count,
            expected_sum=ground_truth.total_debit_movements,
        )


@pytest.mark.asyncio
async def test_repody_vlm_extract_list_fields_via_mock(statement_model_router, ground_truth):
    bundle = load_document_bundle(
        load_bank_statement_bytes(), "application/pdf", settings=get_settings()
    )
    result = await extract_with_repody_vlm(
        bundle,
        list_fields_schema(),
        "Bank statement",
        spec=parse_document_model(REPODY_VLM_CATALOG_ID),
    )
    assert_list_fields(result.fields, ground_truth)


def _llamacpp_live_ready() -> bool:
    base = get_settings().llamacpp_base_url.rstrip("/")
    try:
        return httpx.get(f"{base}/models", timeout=5.0).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture
def live_vlm_required(monkeypatch, disable_extraction_cache):
    monkeypatch.setenv("AUDIT_LLAMACPP_BASE_URL", "http://127.0.0.1:8081/v1")
    monkeypatch.setenv("AUDIT_LLAMACPP_SERVED_MODEL", "nuextract3-q4_k_m")
    get_settings.cache_clear()
    if not _llamacpp_live_ready():
        pytest.skip("llama.cpp / NuExtract not reachable at http://127.0.0.1:8081/v1")


async def _live_extract(schema: list[SchemaFieldSpec], instructions: str):
    result = await extract_document(
        load_bank_statement_bytes(),
        "application/pdf",
        "Bank statement",
        schema,
        extraction_mode="document_model",
        document_model_id=REPODY_VLM_CATALOG_ID,
        extraction_instructions=instructions,
    )
    assert result.meta is not None
    assert result.meta.pages_sent == 2
    return result.fields


@pytest.mark.asyncio
@pytest.mark.live
@pytest.mark.slow
async def test_live_summary_all_scalar_types(ground_truth, live_vlm_required):
    fields = await _live_extract(
        summary_schema(),
        "Bank statement. Extract header and footer scalars only. "
        "Use ISO dates. currency_code must be MAD.",
    )
    for name in (
        "opening_balance",
        "closing_balance",
        "total_debit_movements",
        "total_credit_movements",
    ):
        assert_number_scalar(
            require_field(fields, name),
            getattr(ground_truth, name),
            tolerance=LIVE_SCALAR_TOLERANCE,
        )
    assert_integer_scalar(
        require_field(fields, "debit_transaction_count"), ground_truth.debit_count
    )
    assert_integer_scalar(
        require_field(fields, "credit_transaction_count"), ground_truth.credit_count
    )
    assert_verbatim_contains(require_field(fields, "account_holder"), "EXEMPLE")
    assert_enum_scalar(require_field(fields, "currency_code"), {"MAD"})
    assert_balance_identity(
        parse_numeric_value(require_field(fields, "opening_balance").value) or 0.0,
        parse_numeric_value(require_field(fields, "closing_balance").value) or 0.0,
        parse_numeric_value(require_field(fields, "total_debit_movements").value) or 0.0,
        parse_numeric_value(require_field(fields, "total_credit_movements").value) or 0.0,
        tolerance=5.0,
    )


@pytest.mark.asyncio
@pytest.mark.live
@pytest.mark.slow
async def test_live_number_lists(ground_truth, live_vlm_required):
    fields = await _live_extract(
        list_fields_schema(),
        "Bank statement. Return JSON arrays for every *-list field: one debit amount per "
        "debit line (38), one credit amount per credit line (2), one ISO date per movement "
        "row (40), one description string per row (40).",
    )
    debits = assert_number_list(
        require_field(fields, "transaction_debit_amounts"),
        expected_len=ground_truth.debit_count,
        expected_sum=ground_truth.total_debit_movements,
        sum_tolerance=LIVE_SUM_TOLERANCE,
        len_tolerance=LIVE_LIST_LEN_TOLERANCE,
    )
    credits = assert_number_list(
        require_field(fields, "transaction_credit_amounts"),
        expected_len=ground_truth.credit_count,
        expected_sum=ground_truth.total_credit_movements,
        sum_tolerance=1.0,
    )
    assert_list_not_scalar(require_field(fields, "transaction_debit_amounts"))
    assert_list_not_scalar(require_field(fields, "transaction_credit_amounts"))
    assert len(debits) >= ground_truth.debit_count - LIVE_LIST_LEN_TOLERANCE
    assert round(sum(credits), 2) == ground_truth.total_credit_movements
    assert_date_list(
        require_field(fields, "operation_dates"),
        expected_len=len(ground_truth.movements),
        len_tolerance=LIVE_LIST_LEN_TOLERANCE,
    )
    assert_verbatim_string_list(
        require_field(fields, "transaction_descriptions"),
        expected_len=len(ground_truth.movements),
        must_include=("VERSEMENT", "RETRAIT"),
        len_tolerance=LIVE_LIST_LEN_TOLERANCE,
    )


@pytest.mark.asyncio
@pytest.mark.live
@pytest.mark.slow
async def test_live_object_array_transactions(ground_truth, live_vlm_required):
    fields = await _live_extract(
        transactions_schema(),
        "Bank statement. Return one object per movement row with ISO dates, "
        "verbatim description, enum category, and debit_amount or credit_amount.",
    )
    assert_object_array_transactions(
        require_field(fields, "transactions"),
        ground_truth,
        row_tolerance=LIVE_ROW_TOLERANCE,
        sum_tolerance=LIVE_SUM_TOLERANCE,
    )


@pytest.mark.asyncio
@pytest.mark.live
@pytest.mark.slow
async def test_live_full_schema_combined_types(ground_truth, live_vlm_required):
    fields = await _live_extract(
        full_schema(),
        "Bank statement. Extract ALL fields: header scalars, footer totals, list fields as "
        "JSON arrays, and the transactions object-array. Do not collapse lists into a number.",
    )
    assert_number_scalar(
        require_field(fields, "total_debit_movements"),
        ground_truth.total_debit_movements,
        tolerance=LIVE_SCALAR_TOLERANCE,
    )
    assert_number_list(
        require_field(fields, "transaction_debit_amounts"),
        expected_len=ground_truth.debit_count,
        expected_sum=ground_truth.total_debit_movements,
        sum_tolerance=LIVE_SUM_TOLERANCE,
        len_tolerance=LIVE_LIST_LEN_TOLERANCE,
    )
    assert_date_list(
        require_field(fields, "operation_dates"),
        expected_len=len(ground_truth.movements),
        len_tolerance=LIVE_LIST_LEN_TOLERANCE,
    )
    assert_object_array_transactions(
        require_field(fields, "transactions"),
        ground_truth,
        row_tolerance=LIVE_ROW_TOLERANCE,
        sum_tolerance=LIVE_SUM_TOLERANCE,
    )
    assert normalize_amount(require_field(fields, "opening_balance").value) == normalize_amount(
        "48 250,00"
    )
