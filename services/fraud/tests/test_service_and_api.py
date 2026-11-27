"""Integration-style API and service pipeline tests for ``repody_fraud``."""

import hashlib
import json
from typing import Any

from httpx import ASGITransport, AsyncClient
from tests.conftest import make_clean_pdf, make_tampered_incremental_pdf

from repody_common.contracts import (
    ArtifactRef,
    CaseRef,
    FraudPostVerifyInput,
    FraudPreCheckInput,
)
from repody_fraud.api.deps import get_storage, get_store
from repody_fraud.main import create_app


async def test_standalone_rest_api_analyzes_pdf_json_and_serves_artifacts(
    fraud_store: Any,
    fraud_storage: Any,
) -> None:
    app = create_app()
    app.dependency_overrides[get_store] = lambda: fraud_store
    app.dependency_overrides[get_storage] = lambda: fraud_storage

    tampered = make_tampered_incremental_pdf()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        live = await client.get("/v1/healthz/live")
        assert live.status_code == 200

        res = await client.post(
            "/v1/analyses",
            files=[("files", ("tampered.pdf", tampered, "application/pdf"))],
            data={"extracted_data": json.dumps({"iban": "DE00BADIBAN"})},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["risk_score"] >= 80
        assert body["severity"] == "critical"
        assert body["short_circuit_recommended"] is True
        assert body["requires_four_eyes"] is True
        codes = {f["code"] for f in body["findings"]}
        assert "PDF_REVISION_VISUAL_CHANGE" in codes
        assert "INVALID_IBAN" in codes
        assert len(body["generated_artifacts"]) >= 1

        art_id = body["generated_artifacts"][0]["artifact_id"]
        art_res = await client.get(f"/v1/analyses/{body['id']}/artifacts/{art_id}")
        assert art_res.status_code == 200
        assert art_res.content.startswith(b"\x89PNG")

        fetched = await client.get(f"/v1/analyses/{body['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == body["id"]


async def test_pre_check_detects_template_reuse_and_chains_post_verify(
    fraud_service: Any,
    fraud_storage: Any,
) -> None:
    clean_pdf = make_clean_pdf("RECYCLED INVOICE")
    sha = hashlib.sha256(clean_pdf).hexdigest()
    await fraud_storage.put_bytes("cases/c1/doc.pdf", clean_pdf, "application/pdf")
    await fraud_storage.put_bytes("cases/c2/doc.pdf", clean_pdf, "application/pdf")

    art1 = ArtifactRef(
        artifact_id="art-c1",
        module="core",
        kind="source_document",
        storage_key="cases/c1/doc.pdf",
        sha256=sha,
        mime_type="application/pdf",
        byte_size=len(clean_pdf),
    )
    first = await fraud_service.run_pre_check(
        FraudPreCheckInput(case=CaseRef(case_id="case-1", artifacts=[art1]), artifacts=[art1])
    )
    assert first.risk_score == 0
    assert first.short_circuit_recommended is False

    # Submitting the exact same template on a different case triggers TEMPLATE_REUSE_DETECTED.
    art2 = art1.model_copy(update={"artifact_id": "art-c2", "storage_key": "cases/c2/doc.pdf"})
    second = await fraud_service.run_pre_check(
        FraudPreCheckInput(case=CaseRef(case_id="case-2", artifacts=[art2]), artifacts=[art2])
    )
    assert any(f.code == "TEMPLATE_REUSE_DETECTED" for f in second.findings)

    post = await fraud_service.run_post_verify(
        FraudPostVerifyInput(
            case=CaseRef(case_id="case-1", artifacts=[art1]),
            artifacts=[art1],
            extracted_data={"subtotal": "100.00", "tax": "20.00", "total": "150.00"},
            pre_check_analysis_id=first.analysis_id,
        )
    )
    assert post.requires_four_eyes is True
    assert any(f.code == "MATH_TOTAL_MISMATCH" for f in post.findings)
