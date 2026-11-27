"""Unit tests for the IDP stage contract schemas and output builder."""

import pytest

from repody.app.errors import AppError
from repody.app.stage import build_stage_output
from repody.infra.models import ExtractedField, Run, RunDocument
from repody.schemas.stage import CONTRACT_VERSION, ArtifactRef, CaseRef, IdpStageInput


def _artifact(artifact_id: str = "art-1") -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        module="core",
        kind="source_document",
        storage_key=f"cases/case-1/{artifact_id}.pdf",
        sha256="a" * 64,
        mime_type="application/pdf",
        byte_size=1234,
    )


def test_stage_input_defaults_and_contract_version() -> None:
    artifact = _artifact()
    payload = IdpStageInput(
        case=CaseRef(case_id="case-1", account_id="acc-1", artifacts=[artifact]),
        workflow_id="wf-1",
        artifacts=[artifact],
    )
    assert payload.contract_version == CONTRACT_VERSION
    assert payload.case.input_payload == {}


def test_build_stage_output_handles_unique_and_duplicate_document_types() -> None:
    run = Run(
        id="run-1",
        workflow_id="wf-1",
        source="api",
        status="done",
        outcome="warning",
        definition={},
    )
    run.documents = [
        RunDocument(
            id="rdoc-1",
            run_id="run-1",
            position=0,
            document_id="d-inv",
            document_type="Invoice",
            file_name="inv.pdf",
            mime_type="application/pdf",
            storage_key="runs/run-1/0",
            extraction={"pages_sent": 2, "fields_extracted": 1},
            fields=[
                ExtractedField(
                    id="f1",
                    position=0,
                    key="total_amount",
                    type="number",
                    value=6000,
                    flagged=True,
                )
            ],
        ),
        RunDocument(
            id="rdoc-2",
            run_id="run-1",
            position=1,
            document_id="d-id-1",
            document_type="IDCard",
            file_name="front.png",
            mime_type="image/png",
            storage_key="runs/run-1/1",
            extraction={"pages_sent": 1, "fields_extracted": 1},
            fields=[
                ExtractedField(
                    id="f2",
                    position=0,
                    key="full_name",
                    type="string",
                    value="Alice",
                    flagged=False,
                )
            ],
        ),
        RunDocument(
            id="rdoc-3",
            run_id="run-1",
            position=2,
            document_id="d-id-2",
            document_type="IDCard",
            file_name="back.png",
            mime_type="image/png",
            storage_key="runs/run-1/2",
            extraction={"pages_sent": 1, "fields_extracted": 1},
            fields=[
                ExtractedField(
                    id="f3",
                    position=0,
                    key="mrz",
                    type="string",
                    value="P<FRA",
                    flagged=False,
                )
            ],
        ),
    ]

    output = build_stage_output(run)
    assert output.idp_run_id == "run-1"
    assert output.outcome == "warning"
    assert output.pages_processed == 4
    assert output.flagged_fields == ["Invoice.total_amount"]
    assert output.extracted_data == {
        "Invoice": {"total_amount": 6000},
        "IDCard_1": {"full_name": "Alice"},
        "IDCard_2": {"mrz": "P<FRA"},
    }


def test_build_stage_output_requires_done_run() -> None:
    run = Run(
        id="run-failed",
        workflow_id="wf-1",
        source="api",
        status="failed",
        outcome=None,
        error="Model timeout",
        definition={},
    )
    with pytest.raises(AppError) as exc_info:
        build_stage_output(run)
    assert exc_info.value.status_code == 500
    assert "Model timeout" in exc_info.value.detail
