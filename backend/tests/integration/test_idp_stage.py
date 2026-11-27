"""Integration tests for ``idp.extract_and_validate`` stage bridge."""

import hashlib
import io
import json

import pytest

from repody.app.errors import AppError
from repody.app.stage import execute_idp_stage
from repody.infra.storage import get_store
from repody.schemas.stage import ArtifactRef, CaseRef, IdpStageInput
from tests.files import PDF
from tests.integration.helpers import condition, invoice_workflow, rule


async def _deploy_invoice_workflow(api, workflow_id: str = "wf-stage") -> None:
    await api.put(
        f"/v1/workflows/{workflow_id}",
        json=invoice_workflow(rule("total", condition("total_amount", "==", "6000"))),
    )
    res = await api.post(f"/v1/workflows/{workflow_id}/deploy")
    assert res.status_code == 200, res.text


async def _stage_pdf_artifact(
    key: str = "cases/case-1/facture.pdf", sha: str | None = None
) -> ArtifactRef:
    await get_store().put(key, io.BytesIO(PDF), "application/pdf")
    return ArtifactRef(
        artifact_id="art-pdf-1",
        module="core",
        kind="source_document",
        storage_key=key,
        sha256=sha or hashlib.sha256(PDF).hexdigest(),
        mime_type="application/pdf",
        byte_size=len(PDF),
    )


async def test_execute_idp_stage_extracts_and_is_idempotent(api, model_answer) -> None:
    await _deploy_invoice_workflow(api)
    artifact = await _stage_pdf_artifact()
    model_answer["text"] = json.dumps({"total_amount": 6000, "tva": 1000})

    payload = IdpStageInput(
        case=CaseRef(case_id="case-1", artifacts=[artifact]),
        workflow_id="wf-stage",
        artifacts=[artifact],
    )
    first = await execute_idp_stage(payload)
    assert first.outcome == "passed"
    assert first.extracted_data == {"Invoice": {"total_amount": 6000, "tva": 1000}}
    assert first.flagged_fields == []
    assert first.pages_processed >= 1
    first_call_count = len(model_answer["calls"])
    assert first_call_count >= 1

    # Re-running the same (case_id, workflow_id) stage returns the prior result cleanly.
    second = await execute_idp_stage(payload)
    assert second == first
    assert len(model_answer["calls"]) == first_call_count
    # Core's immutable artifact key stays intact in S3.
    assert await get_store().get(artifact.storage_key) == PDF


async def test_execute_idp_stage_rejects_sha256_mismatch(api, model_answer) -> None:
    await _deploy_invoice_workflow(api)
    bad_artifact = await _stage_pdf_artifact(sha="0" * 64)
    payload = IdpStageInput(
        case=CaseRef(case_id="case-bad-sha", artifacts=[bad_artifact]),
        workflow_id="wf-stage",
        artifacts=[bad_artifact],
    )
    with pytest.raises(AppError) as exc_info:
        await execute_idp_stage(payload)
    assert exc_info.value.status_code == 422
    assert "SHA-256 mismatch" in exc_info.value.detail
    assert model_answer["calls"] == []


async def test_execute_idp_stage_rejects_undeployed_workflow(api, model_answer) -> None:
    await api.put("/v1/workflows/wf-draft", json=invoice_workflow())
    artifact = await _stage_pdf_artifact("cases/case-draft/facture.pdf")
    payload = IdpStageInput(
        case=CaseRef(case_id="case-draft", artifacts=[artifact]),
        workflow_id="wf-draft",
        artifacts=[artifact],
    )
    with pytest.raises(AppError) as exc_info:
        await execute_idp_stage(payload)
    assert exc_info.value.status_code == 409
    assert "not deployed" in exc_info.value.detail.lower()
    assert model_answer["calls"] == []
