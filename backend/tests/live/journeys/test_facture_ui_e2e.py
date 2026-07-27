"""
Facture E2E via the same HTTP flow as the UI Test tab (workflow-run).

Uses:
  PUT  /v1/workflows/{id}          — save documents + read path + validationMode
  POST /v1/workflows/{id}/runs   — multipart payload + document_ids + files
  GET  /v1/runs/{id}/status       — poll (then GET /v1/runs/{id} for result)

Requires a running docker stack with Taskiq workers:
  E2E_STACK=1 E2E_API_URL=http://localhost:8000 pnpm test:api:live
"""

from __future__ import annotations

import httpx
import pytest

from audit_workbench.integration.facture import (
    EXPECTED_TOTAL,
    EXPECTED_TVA,
    FACTURE_PDF,
    FACTURE_UI_PATHS,
    LOGIC_RULE_TOTAL_FAIL,
    LOGIC_RULE_TOTAL_OK,
    LOGIC_RULE_TVA_UNDER_500,
    LOGIC_RULE_TVA_UNDER_500_UI_CONDITIONS,
    WORKFLOW_NAME,
    FacturePathCase,
    document_def,
    document_def_tva,
    facture_bytes,
    new_doc_id,
    rule_status_from_result,
    rules_for_case,
    total_from_result,
    tva_from_result,
)
from audit_workbench.integration.workflow_flow import run_test_with_files, save_workflow

pytestmark = [pytest.mark.e2e_facture, pytest.mark.live, pytest.mark.asyncio]

requires_facture = pytest.mark.skipif(
    not FACTURE_PDF.is_file(),
    reason="Facture.pdf fixture missing",
)


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
async def test_stack_facture_tva_under_500(live_client):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_tva_case(
        live_client,
        case,
        rules=[LOGIC_RULE_TVA_UNDER_500],
    )
    tva = _normalize_amount(tva_from_result(result))
    assert tva is not None, "TVA field was not extracted"
    assert abs(tva - 1000.0) < 1.0, f"Expected TVA ~1000, got {tva_from_result(result)!r}"
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TVA_UNDER_500["name"]) == "failed"
    assert result["status"] == "failed"


@requires_facture
async def test_ui_facture_validation_from_ui_conditions_only(live_client):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_tva_case(
        live_client,
        case,
        rules=[LOGIC_RULE_TVA_UNDER_500_UI_CONDITIONS],
    )
    assert tva_from_result(result) == EXPECTED_TVA
    rule_results = result.get("ruleResults") or []
    assert any(r.get("status") == "failed" for r in rule_results), rule_results
    assert "skipped" not in (rule_results[0].get("detail") or "").lower()
    assert result["status"] == "failed"


@requires_facture
async def test_ui_facture_tva_under_500(live_client):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_tva_case(
        live_client,
        case,
        rules=[LOGIC_RULE_TVA_UNDER_500],
    )
    assert tva_from_result(result) == EXPECTED_TVA
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TVA_UNDER_500["name"]) == "failed"
    assert result["status"] == "failed"


@requires_facture
async def test_ui_document_model_logic(live_client):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_case(live_client, case)
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_OK["name"]) == "passed"


@requires_facture
async def test_ui_document_model_logic_fails_wrong_rule(live_client):
    doc_id = new_doc_id()
    case = FACTURE_UI_PATHS[0]
    documents = [document_def(case, doc_id=doc_id)]
    rules = [LOGIC_RULE_TOTAL_FAIL]
    wf_id = await save_workflow(
        live_client,
        wf_id="wf-facture-fail",
        name=WORKFLOW_NAME,
        documents=documents,
        rules=rules,
    )
    pdf = facture_bytes()
    result = await run_test_with_files(
        live_client,
        wf_id,
        documents=documents,
        rules=rules,
        workflow_name=WORKFLOW_NAME,
        files_by_doc_id={doc_id: ("Facture.pdf", pdf, "application/pdf")},
    )
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_FAIL["name"]) == "failed"


@requires_facture
async def test_stack_document_model_logic(live_client):
    case = FACTURE_UI_PATHS[0]
    result = await _run_facture_case(live_client, case)
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_OK["name"]) == "passed"
