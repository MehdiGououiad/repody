"""Unit tests for cross-service contracts and Four-Eyes enforcement."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from repody_common.contracts import (
    ArtifactRef,
    CaseRef,
    FourEyesApprovalEvent,
    FraudPostVerifyOutput,
)
from repody_common.ids import new_id


def test_case_ref_supports_zero_document_payloads() -> None:
    case = CaseRef(
        case_id=new_id("case"),
        account_id="client-bank-a",
        input_payload={"portal_url": "https://core.internal", "transfer_ref": "TX-99"},
    )
    assert case.case_id.startswith("case-")
    assert case.artifacts == []
    assert case.input_payload["transfer_ref"] == "TX-99"


def test_four_eyes_approval_rejects_same_maker_and_checker() -> None:
    digest = "a" * 64
    now = datetime(2026, 11, 27, 15, 0, tzinfo=UTC)
    with pytest.raises(ValidationError, match="Four-eyes violation"):
        FourEyesApprovalEvent(
            approval_id=new_id("apr"),
            case_id=new_id("case"),
            payload_sha256=digest,
            maker_sub="user-1",
            checker_sub="user-1",
            decision="approved",
            decided_at=now,
        )

    valid = FourEyesApprovalEvent(
        approval_id=new_id("apr"),
        case_id=new_id("case"),
        payload_sha256=digest,
        maker_sub="user-1",
        checker_sub="user-2",
        decision="approved",
        note="Verified against source scan.",
        decided_at=now,
    )
    assert valid.checker_sub != valid.maker_sub


def test_fraud_post_verify_contract_round_trip() -> None:
    art = ArtifactRef(
        artifact_id=new_id("art"),
        module="fraud",
        kind="forensic_heatmap",
        storage_key="cases/1/heatmap.png",
        sha256="b" * 64,
        mime_type="image/png",
        byte_size=4096,
    )
    out = FraudPostVerifyOutput(
        analysis_id=new_id("frd"),
        risk_score=82,
        severity="high",
        requires_four_eyes=True,
        generated_artifacts=[art],
    )
    restored = FraudPostVerifyOutput.model_validate_json(out.model_dump_json())
    assert restored == out
