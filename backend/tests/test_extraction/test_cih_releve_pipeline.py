"""Hard tests for the NuExtract extraction pipeline on the CIH relevé PDF."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from audit_workbench.catalog.registry import parse_document_model
from audit_workbench.extraction.base import ExtractedFieldResult, SchemaFieldSpec
from audit_workbench.extraction.document_bundle import load_document_bundle
from audit_workbench.extraction.field_json import normalize_amount, parse_fields_json, parse_numeric_value
from audit_workbench.extraction.nuextract_contract import (
    NUEXTRACT_ENABLE_THINKING,
    NUEXTRACT_MAX_PAGES_PER_REQUEST,
)
from audit_workbench.extraction.nuextract_template import build_vlm_template
from audit_workbench.extraction.pipeline import PipelineExtractor
from audit_workbench.extraction.repody_vlm import REPODY_VLM_CATALOG_ID
from audit_workbench.extraction.repody_vlm_extract import extract_with_repody_vlm
from audit_workbench.extraction.repody_vlm_pages import _encode_pages_for_vlm, _vlm_pages
from audit_workbench.extraction.repody_vlm_payloads import _fields_payload, _structured_payload
from audit_workbench.inference.factory import get_inference_client
from audit_workbench.settings import get_settings
from tests.fixtures.cih_releve_assertions import (
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
from tests.fixtures.cih_releve_ground_truth import (
    all_cih_schema_fields,
    build_cih_model_payload,
    cih_debit_list_schema,
    cih_full_schema,
    cih_list_fields_schema,
    cih_releve_pdf_path,
    cih_summary_schema,
    cih_transactions_schema,
    get_cih_releve_ground_truth,
    load_cih_releve_bytes,
    parse_cih_releve_ground_truth,
)
from tests.llm_mocks import disable_dmr_mock, enable_dmr_mock

pytestmark = pytest.mark.skipif(
    not cih_releve_pdf_path().is_file(),
    reason="CIH relevé PDF fixture missing",
)

LIVE_LIST_LEN_TOLERANCE = 1
LIVE_SUM_TOLERANCE = 100.0
LIVE_ROW_TOLERANCE = 2
LIVE_SCALAR_TOLERANCE = 1.0


@pytest.fixture
def ground_truth():
    return get_cih_releve_ground_truth()


@pytest.fixture
def disable_extraction_cache(monkeypatch):
    monkeypatch.setenv("AUDIT_EXTRACTION_CACHE_ENABLED", "false")
    get_settings.cache_clear()
    monkeypatch.setattr("audit_workbench.extraction.pipeline.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr("audit_workbench.extraction.pipeline.set_cached", AsyncMock())


@pytest.fixture
def live_llamacpp(monkeypatch, disable_extraction_cache):
    monkeypatch.setenv("AUDIT_LLAMACPP_BASE_URL", "http://127.0.0.1:8081/v1")
    monkeypatch.setenv("AUDIT_LLAMACPP_SERVED_MODEL", "nuextract3-q4_k_m")
    get_settings.cache_clear()
    get_inference_client.cache_clear()
    if not _llamacpp_live_ready():
        pytest.skip("llama.cpp / NuExtract not reachable at http://127.0.0.1:8081/v1")


def test_cih_fixture_ground_truth_matches_statement_footer():
    from tests.fixtures.cih_releve_ground_truth import load_cih_releve_text

    gt = parse_cih_releve_ground_truth(load_cih_releve_text())
    assert gt.page_count == 2
    assert gt.account_holder == "JARROUMI SAFAA"
    assert gt.account_number == "2828613211020200"
    assert gt.agency == "SIDI BENNOUR"
    assert gt.currency == "MAD"
    assert gt.opening_balance == 77_224.44
    assert gt.closing_balance == 34_908.37
    assert gt.total_debit_movements == 92_316.07
    assert gt.total_credit_movements == 50_000.00
    assert gt.debit_count == 38
    assert gt.credit_count == 2
    assert len(gt.transactions) == 40
    assert len(gt.operation_dates_iso) == 40
    assert len(gt.transaction_descriptions) == 40
    assert set(gt.movement_categories) >= {"DEPOSIT", "WITHDRAWAL", "CARD", "FEE", "TRANSFER"}
    assert_balance_identity(
        gt.opening_balance,
        gt.closing_balance,
        gt.total_debit_movements,
        gt.total_credit_movements,
    )


def test_cih_pdf_renders_two_png_pages_without_cap(ground_truth):
    bundle = load_document_bundle(
        load_cih_releve_bytes(),
        "application/pdf",
        settings=get_settings(),
    )
    pages, rendered = _vlm_pages(bundle)
    assert rendered == ground_truth.page_count == 2
    assert len(pages) == 2
    assert all(mime == "image/png" for _, mime in pages)
    assert all(len(raw) > 500 for raw, _ in pages)
    assert rendered <= NUEXTRACT_MAX_PAGES_PER_REQUEST


def test_cih_full_template_covers_scalar_list_and_object_array():
    template = build_vlm_template(cih_full_schema())
    assert template["opening_balance"] == "number"
    assert template["debit_transaction_count"] == "integer"
    assert template["opening_balance_date"] == "date"
    assert template["currency"] == "currency"
    assert template["currency_code"] == ["MAD", "EUR", "USD"]
    assert template["transaction_debit_amounts"] == ["number"]
    assert template["operation_dates"] == ["date"]
    assert template["transaction_descriptions"] == ["verbatim-string"]
    assert template["movement_categories"] == [["DEPOSIT", "TRANSFER", "WITHDRAWAL", "CARD", "FEE", "OTHER"]]
    row = template["transactions"][0]
    assert row["operation_date"] == "date"
    assert row["value_date"] == "date"
    assert row["category"] == ["DEPOSIT", "TRANSFER", "WITHDRAWAL", "CARD", "FEE", "OTHER"]


@pytest.mark.parametrize(
    ("schema_factory", "field_name", "expected_template"),
    [
        (cih_summary_schema, "opening_balance", "number"),
        (cih_summary_schema, "debit_transaction_count", "integer"),
        (cih_summary_schema, "opening_balance_date", "date"),
        (cih_summary_schema, "currency", "currency"),
        (cih_debit_list_schema, "transaction_debit_amounts", ["number"]),
        (cih_list_fields_schema, "operation_dates", ["date"]),
        (cih_list_fields_schema, "transaction_descriptions", ["verbatim-string"]),
    ],
)
def test_cih_schema_template_types(schema_factory, field_name, expected_template):
    template = build_vlm_template(schema_factory())
    assert template[field_name] == expected_template


def _parse_golden_fields(schema: list[SchemaFieldSpec]) -> list[ExtractedFieldResult]:
    raw = json.dumps(build_cih_model_payload(schema))
    return parse_fields_json(_fields_payload(raw, schema), schema)


def assert_summary_fields(fields: list[ExtractedFieldResult], ground_truth) -> None:
    assert_verbatim_contains(require_field(fields, "account_holder"), "JARROUMI", "SAFAA")
    assert_verbatim_contains(require_field(fields, "agency"), "SIDI", "BENNOUR")
    assert_number_scalar(require_field(fields, "opening_balance"), ground_truth.opening_balance)
    assert_number_scalar(require_field(fields, "closing_balance"), ground_truth.closing_balance)
    assert_number_scalar(require_field(fields, "total_debit_movements"), ground_truth.total_debit_movements)
    assert_number_scalar(require_field(fields, "total_credit_movements"), ground_truth.total_credit_movements)
    assert_integer_scalar(require_field(fields, "debit_transaction_count"), ground_truth.debit_count)
    assert_integer_scalar(require_field(fields, "credit_transaction_count"), ground_truth.credit_count)
    assert_date_scalar(require_field(fields, "opening_balance_date"), ground_truth.opening_balance_iso)
    assert_date_scalar(require_field(fields, "closing_balance_date"), ground_truth.closing_balance_iso)
    assert_currency_scalar(require_field(fields, "currency"), "MAD", "DIRHAM")
    assert_enum_scalar(require_field(fields, "currency_code"), {"MAD", "EUR", "USD"})
    assert require_field(fields, "account_number").value == ground_truth.account_number


def assert_list_fields(fields: list[ExtractedFieldResult], ground_truth) -> None:
    debits = assert_number_list(
        require_field(fields, "transaction_debit_amounts"),
        expected_len=ground_truth.debit_count,
        expected_sum=ground_truth.total_debit_movements,
    )
    credits = assert_number_list(
        require_field(fields, "transaction_credit_amounts"),
        expected_len=ground_truth.credit_count,
        expected_sum=ground_truth.total_credit_movements,
    )
    dates = assert_date_list(
        require_field(fields, "operation_dates"),
        expected_len=len(ground_truth.transactions),
    )
    descriptions = assert_verbatim_string_list(
        require_field(fields, "transaction_descriptions"),
        expected_len=len(ground_truth.transactions),
        must_include=("VERSEMENT", "RETRAIT CARTE", "PAIEMENT PAR CARTE"),
    )
    assert_multi_enum(
        require_field(fields, "movement_categories"),
        {"DEPOSIT", "WITHDRAWAL", "CARD", "FEE", "TRANSFER"},
    )
    assert debits[0] == ground_truth.debit_amounts[0]
    assert debits[-1] == ground_truth.debit_amounts[-1]
    assert credits == [10_000.0, 40_000.0]
    assert dates[0] in {ground_truth.operation_dates_iso[0], "28/02", "28/02/2022"}
    assert "VERSEMENT" in descriptions[6].upper()
    assert "RETRAIT PAR CHEQUE" in descriptions[5].upper()


def assert_transactions_field(fields: list[ExtractedFieldResult], ground_truth) -> None:
    rows = assert_object_array_transactions(require_field(fields, "transactions"), ground_truth)
    first = rows[0]
    assert parse_numeric_value(str(first.get("debit_amount"))) == ground_truth.debit_amounts[0]
    credit_row = next(r for r in rows if r.get("credit_amount") not in (None, "", "—", "null"))
    assert parse_numeric_value(str(credit_row.get("credit_amount"))) == 10_000.0


def test_golden_summary_scalar_types(ground_truth):
    assert_summary_fields(_parse_golden_fields(cih_summary_schema()), ground_truth)


def test_golden_list_field_types(ground_truth):
    assert_list_fields(_parse_golden_fields(cih_list_fields_schema()), ground_truth)


def test_golden_object_array_nested_types(ground_truth):
    assert_transactions_field(_parse_golden_fields(cih_transactions_schema()), ground_truth)


@pytest.mark.parametrize(
    ("bad_json", "field_name"),
    [
        ('{"transaction_debit_amounts": 92316.07}', "transaction_debit_amounts"),
        ('{"transaction_debit_amounts": "92316.07"}', "transaction_debit_amounts"),
        ('{"operation_dates": "2022-03-01"}', "operation_dates"),
        ('{"transactions": {"operation_date": "2022-03-01"}}', "transactions"),
    ],
)
def test_rejects_wrong_json_shapes_for_list_and_object_fields(bad_json, field_name):
    schema = cih_full_schema()
    wrapped = _fields_payload(bad_json, schema)
    field = field_map(parse_fields_json(wrapped, schema))[field_name]
    if field_name.endswith("_amounts") or field_name == "operation_dates":
        with pytest.raises((json.JSONDecodeError, AssertionError)):
            parsed = assert_is_json_list(field.value, field_name=field_name)
            assert isinstance(parsed, list)
    if field_name == "transactions":
        parsed = json.loads(field.value)
        assert not isinstance(parsed, list)


def _cih_inference_side_effect(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode())
    template_raw = (payload.get("chat_template_kwargs") or {}).get("template")
    if not template_raw:
        return httpx.Response(500, json={"error": "missing template"})
    template = json.loads(template_raw)
    registry = all_cih_schema_fields()
    schema = [registry.get(name, SchemaFieldSpec(name=name)) for name in template]
    mock_body = build_cih_model_payload(schema)
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": json.dumps(mock_body)}}]},
    )


@pytest.fixture
def cih_respx_router(monkeypatch):
    base = "http://cih-extract-mock.test/v1"
    router = enable_dmr_mock(monkeypatch, base=base)
    router.post(f"{base}/chat/completions").mock(side_effect=_cih_inference_side_effect)
    yield router
    disable_dmr_mock(router)


@pytest.mark.asyncio
async def test_pipeline_mocked_full_schema_all_types(
    cih_respx_router,
    ground_truth,
    disable_extraction_cache,
):
    result = await PipelineExtractor().extract(
        load_cih_releve_bytes(),
        "application/pdf",
        "Bank statement",
        cih_full_schema(),
        extraction_mode="document_model",
        document_model_id=REPODY_VLM_CATALOG_ID,
        extraction_instructions="CIH relevé de compte — extract all fields exactly.",
    )
    assert result.meta is not None
    assert result.meta.pages_rendered == 2
    assert result.meta.pages_sent == 2
    assert result.meta.pages_dropped == 0
    assert_summary_fields(result.fields, ground_truth)
    assert_list_fields(result.fields, ground_truth)
    assert_transactions_field(result.fields, ground_truth)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "schema_factory",
    [cih_summary_schema, cih_list_fields_schema, cih_transactions_schema, cih_debit_list_schema],
)
async def test_pipeline_mocked_per_schema(
    schema_factory,
    cih_respx_router,
    ground_truth,
    disable_extraction_cache,
):
    schema = schema_factory()
    result = await PipelineExtractor().extract(
        load_cih_releve_bytes(),
        "application/pdf",
        "Bank statement",
        schema,
        extraction_mode="document_model",
        document_model_id=REPODY_VLM_CATALOG_ID,
    )
    assert result.meta is not None
    assert result.meta.pages_sent == 2
    if schema_factory is cih_summary_schema:
        assert_summary_fields(result.fields, ground_truth)
    elif schema_factory is cih_list_fields_schema:
        assert_list_fields(result.fields, ground_truth)
    elif schema_factory is cih_transactions_schema:
        assert_transactions_field(result.fields, ground_truth)
    elif schema_factory is cih_debit_list_schema:
        assert_number_list(
            require_field(result.fields, "transaction_debit_amounts"),
            expected_len=ground_truth.debit_count,
            expected_sum=ground_truth.total_debit_movements,
        )


@pytest.mark.asyncio
async def test_repody_vlm_extract_list_fields_via_mock(cih_respx_router, ground_truth):
    bundle = load_document_bundle(
        load_cih_releve_bytes(),
        "application/pdf",
        settings=get_settings(),
    )
    result = await extract_with_repody_vlm(
        bundle,
        cih_list_fields_schema(),
        "Bank statement",
        spec=parse_document_model(REPODY_VLM_CATALOG_ID),
    )
    assert_list_fields(result.fields, ground_truth)


def _llamacpp_live_ready() -> bool:
    base = get_settings().llamacpp_base_url.rstrip("/")
    try:
        response = httpx.get(f"{base}/models", timeout=5.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture
def live_vlm_required(live_llamacpp):
    return live_llamacpp


async def _live_extract(
    schema: list[SchemaFieldSpec],
    *,
    instructions: str,
    disable_extraction_cache,
) -> list[ExtractedFieldResult]:
    result = await PipelineExtractor().extract(
        load_cih_releve_bytes(),
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
async def test_live_cih_summary_all_scalar_types(ground_truth, disable_extraction_cache, live_vlm_required):
    fields = await _live_extract(
        cih_summary_schema(),
        instructions=(
            "Moroccan CIH relevé de compte. Extract header/footer scalars only. "
            "Use ISO dates. currency_code must be MAD."
        ),
        disable_extraction_cache=disable_extraction_cache,
    )
    assert_number_scalar(
        require_field(fields, "opening_balance"),
        ground_truth.opening_balance,
        tolerance=LIVE_SCALAR_TOLERANCE,
    )
    assert_number_scalar(
        require_field(fields, "closing_balance"),
        ground_truth.closing_balance,
        tolerance=LIVE_SCALAR_TOLERANCE,
    )
    assert_number_scalar(
        require_field(fields, "total_debit_movements"),
        ground_truth.total_debit_movements,
        tolerance=LIVE_SCALAR_TOLERANCE,
    )
    assert_number_scalar(
        require_field(fields, "total_credit_movements"),
        ground_truth.total_credit_movements,
        tolerance=LIVE_SCALAR_TOLERANCE,
    )
    assert_integer_scalar(
        require_field(fields, "debit_transaction_count"),
        ground_truth.debit_count,
    )
    assert_integer_scalar(
        require_field(fields, "credit_transaction_count"),
        ground_truth.credit_count,
    )
    assert_verbatim_contains(require_field(fields, "account_holder"), "JARROUMI")
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
async def test_live_cih_number_lists(ground_truth, disable_extraction_cache, live_vlm_required):
    fields = await _live_extract(
        cih_list_fields_schema(),
        instructions=(
            "CIH relevé de compte. Return JSON arrays for every *-list field: "
            "one debit amount per debit line (38), one credit amount per credit line (2), "
            "one ISO date per movement row (40), one description string per row (40)."
        ),
        disable_extraction_cache=disable_extraction_cache,
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
        len_tolerance=0,
    )
    assert_list_not_scalar(require_field(fields, "transaction_debit_amounts"))
    assert_list_not_scalar(require_field(fields, "transaction_credit_amounts"))
    assert len(debits) >= ground_truth.debit_count - LIVE_LIST_LEN_TOLERANCE
    assert credits == [10_000.0, 40_000.0] or round(sum(credits), 2) == 50_000.0
    assert_date_list(
        require_field(fields, "operation_dates"),
        expected_len=len(ground_truth.transactions),
        len_tolerance=LIVE_LIST_LEN_TOLERANCE,
    )
    assert_verbatim_string_list(
        require_field(fields, "transaction_descriptions"),
        expected_len=len(ground_truth.transactions),
        must_include=("VERSEMENT", "RETRAIT"),
        len_tolerance=LIVE_LIST_LEN_TOLERANCE,
    )


@pytest.mark.asyncio
@pytest.mark.live
@pytest.mark.slow
async def test_live_cih_object_array_transactions(ground_truth, disable_extraction_cache, live_vlm_required):
    fields = await _live_extract(
        cih_transactions_schema(),
        instructions=(
            "CIH relevé de compte. Return one object per movement row with ISO dates, "
            "verbatim description, enum category, and debit_amount or credit_amount."
        ),
        disable_extraction_cache=disable_extraction_cache,
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
async def test_live_cih_full_schema_combined_types(ground_truth, disable_extraction_cache, live_vlm_required):
    fields = await _live_extract(
        cih_full_schema(),
        instructions=(
            "Moroccan CIH bank statement (relevé). Extract ALL fields: header scalars, "
            "footer totals, list fields as JSON arrays, and transactions object-array. "
            "Do not collapse lists into a single number."
        ),
        disable_extraction_cache=disable_extraction_cache,
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
        expected_len=len(ground_truth.transactions),
        len_tolerance=LIVE_LIST_LEN_TOLERANCE,
    )
    assert_object_array_transactions(
        require_field(fields, "transactions"),
        ground_truth,
        row_tolerance=LIVE_ROW_TOLERANCE,
        sum_tolerance=LIVE_SUM_TOLERANCE,
    )
    assert normalize_amount(require_field(fields, "opening_balance").value) == normalize_amount("77 224,44")
