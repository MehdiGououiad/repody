"""
Facture E2E via the same HTTP flow as the UI Test tab (runTestWithFiles).

Uses:
  PUT  /v1/workflows/{id}          — save documents + read path + validationMode
  POST /v1/workflows/{id}/runs?mode=test  — multipart payload + document_ids + files
  GET  /v1/runs/{id}/status       — poll (then GET /v1/runs/{id} for result)

ASGI (local tests): Hatchet dispatch is simulated in pytest (see tests/helpers/hatchet_sim.py).
Stack (`pnpm compose up --stack=dev --detach`): set `E2E_STACK=1` and `E2E_API_URL=http://api:8000` for real workers.
"""

from __future__ import annotations

import os

import httpx
import pytest

from tests.test_e2e.facture_helpers import (
    EXPECTED_TOTAL,
    EXPECTED_TVA,
    FACTURE_PDF,
    FACTURE_UI_PATHS,
    FacturePathCase,
    LOGIC_RULE_TOTAL_FAIL,
    LOGIC_RULE_TOTAL_OK,
    LOGIC_RULE_TVA_UNDER_500,
    LOGIC_RULE_TVA_UNDER_500_UI_CONDITIONS,
    WORKFLOW_NAME,
    document_def,
    document_def_tva,
    facture_bytes,
    new_doc_id,
    rule_status_from_result,
    rules_for_case,
    total_from_result,
    tva_from_result,
)
from tests.test_e2e.ui_flow import run_test_with_files, save_workflow

pytestmark = [pytest.mark.e2e_facture, pytest.mark.asyncio]

requires_facture = pytest.mark.skipif(
    not FACTURE_PDF.is_file(),
    reason="Facture.pdf fixture missing",
)


@pytest.fixture
async def ui_client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def stack_client():
    if os.environ.get("E2E_STACK") != "1":
        pytest.skip("Set E2E_STACK=1 with a running docker stack")
    base = os.environ.get("E2E_API_URL", "http://localhost:8000").rstrip("/")
    async with httpx.AsyncClient(base_url=base, timeout=httpx.Timeout(600.0)) as ac:
        yield ac


async def _run_facture_case(client: httpx.AsyncClient, case: FacturePathCase) -> dict:
    doc_id = new_doc_id()
    documents = [document_def(case, doc_id=doc_id)]
    rules = rules_for_case(case)
    wf_id = await save_workflow(
        client,
        wf_id=f"wf-facture-{case.id}",
        name=WORKFLOW_NAME,
        documents=documents,
        rules=rules,
    )
    pdf = facture_bytes()
    return await run_test_with_files(
        client,
        wf_id,
        documents=documents,
        rules=rules,
        workflow_name=WORKFLOW_NAME,
        files_by_doc_id={doc_id: ("Facture.pdf", pdf, "application/pdf")},
        max_wait_ms=case.max_wait_ms,
    )


async def _run_facture_tva_case(
    client: httpx.AsyncClient,
    case: FacturePathCase,
    *,
    rules: list[dict],
) -> dict:
    doc_id = new_doc_id()
    documents = [document_def_tva(case, doc_id=doc_id)]
    wf_id = await save_workflow(
        client,
        wf_id=f"wf-facture-tva-{case.id}",
        name=WORKFLOW_NAME,
        documents=documents,
        rules=rules,
    )
    pdf = facture_bytes()
    return await run_test_with_files(
        client,
        wf_id,
        documents=documents,
        rules=rules,
        workflow_name=WORKFLOW_NAME,
        files_by_doc_id={doc_id: ("Facture.pdf", pdf, "application/pdf")},
        max_wait_ms=case.max_wait_ms,
    )


def _normalize_amount(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(" ", "").replace(",", ".")
    for token in cleaned.split():
        try:
            return float(token)
        except ValueError:
            continue
    try:
        return float(cleaned)
    except ValueError:
        return None


@requires_facture
@pytest.mark.live
async def test_stack_facture_tva_under_500(stack_client):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_tva_case(
        stack_client,
        case,
        rules=[LOGIC_RULE_TVA_UNDER_500],
    )
    tva = _normalize_amount(tva_from_result(result))
    assert tva is not None, "TVA field was not extracted"
    assert abs(tva - 1000.0) < 1.0, f"Expected TVA ~1000, got {tva_from_result(result)!r}"
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TVA_UNDER_500["name"]) == "failed"
    assert result["status"] == "failed"


@requires_facture
async def test_ui_facture_validation_from_ui_conditions_only(ui_client, mock_ollama_llm):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_tva_case(
        ui_client,
        case,
        rules=[LOGIC_RULE_TVA_UNDER_500_UI_CONDITIONS],
    )
    assert tva_from_result(result) == EXPECTED_TVA
    rule_results = result.get("ruleResults") or []
    assert any(r.get("status") == "failed" for r in rule_results), rule_results
    assert "skipped" not in (rule_results[0].get("detail") or "").lower()
    assert result["status"] == "failed"


@requires_facture
async def test_ui_facture_tva_under_500(ui_client, mock_ollama_llm):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_tva_case(
        ui_client,
        case,
        rules=[LOGIC_RULE_TVA_UNDER_500],
    )
    assert tva_from_result(result) == EXPECTED_TVA
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TVA_UNDER_500["name"]) == "failed"
    assert result["status"] == "failed"


@requires_facture
async def test_ui_document_model_logic(ui_client, mock_ollama_llm):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_case(ui_client, case)
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_OK["name"]) == "passed"


@requires_facture
async def test_ui_document_model_logic_fails_wrong_rule(ui_client, mock_ollama_llm):
    doc_id = new_doc_id()
    case = FACTURE_UI_PATHS[0]
    documents = [document_def(case, doc_id=doc_id)]
    rules = [LOGIC_RULE_TOTAL_FAIL]
    wf_id = await save_workflow(
        ui_client,
        wf_id="wf-facture-fail",
        name=WORKFLOW_NAME,
        documents=documents,
        rules=rules,
    )
    pdf = facture_bytes()
    result = await run_test_with_files(
        ui_client,
        wf_id,
        documents=documents,
        rules=rules,
        workflow_name=WORKFLOW_NAME,
        files_by_doc_id={doc_id: ("Facture.pdf", pdf, "application/pdf")},
    )
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_FAIL["name"]) == "failed"


@requires_facture
@pytest.mark.live
async def test_stack_document_model_logic(stack_client):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_case(stack_client, case)
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_OK["name"]) == "passed"
