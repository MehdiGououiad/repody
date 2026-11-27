"""End-to-end API tests for zero-document cases, offline licensing, and Four-Eyes approvals."""

from typing import Any

from httpx import ASGITransport, AsyncClient

from repody_core.api.deps import get_entitlement_provider, get_publisher, get_store
from repody_core.main import create_app


async def test_end_to_end_four_eyes_and_entitlements(
    core_store: Any,
    core_gateway: Any,
    entitlement_factory: Any,
) -> None:
    entitlements = entitlement_factory(("idp", "fraud"))

    app = create_app()
    app.dependency_overrides[get_store] = lambda: core_store
    app.dependency_overrides[get_publisher] = lambda: core_gateway
    app.dependency_overrides[get_entitlement_provider] = lambda: entitlements

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        live = await client.get("/v1/healthz/live")
        assert live.status_code == 200
        assert live.json()["status"] == "ok"

        ent = await client.get("/v1/platform/entitlements")
        assert ent.status_code == 200
        assert ent.json()["status"] == "active"
        assert ent.json()["modules"] == ["idp", "fraud"]

        # Create a zero-document case (pure JSON payload).
        case_res = await client.post(
            "/v1/cases",
            headers={"X-Dev-User": "alice-maker"},
            json={
                "external_ref": "WIRE-2026-001",
                "input_payload": {"invoice": {"total": "1000.00"}, "iban": "FR763000600001123456"},
            },
        )
        assert case_res.status_code == 201
        case_id = case_res.json()["id"]

        apr_res = await client.post(
            "/v1/approvals",
            headers={"X-Dev-User": "alice-maker"},
            json={
                "case_id": case_id,
                "stage_name": "fraud_and_idp_gate",
                "payload_snapshot": {"invoice": {"total": "1000.00"}},
            },
        )
        assert apr_res.status_code == 201
        apr_id = apr_res.json()["id"]
        initial_hash = apr_res.json()["payload_sha256"]

        # Maker applies an audited override and submits to Checker.
        make_res = await client.post(
            f"/v1/approvals/{apr_id}/make",
            headers={"X-Dev-User": "alice-maker"},
            json={
                "overrides": [
                    {
                        "field_path": "invoice.total",
                        "after_value": "1050.00",
                        "reason": "Confirmed VAT line against PDF scan.",
                    }
                ],
                "note": "Ready for four-eyes check.",
            },
        )
        assert make_res.status_code == 200
        assert make_res.json()["status"] == "waiting_checker"
        assert make_res.json()["payload_sha256"] != initial_hash
        assert make_res.json()["overrides"][0]["before_value"] == "1000.00"
        assert make_res.json()["overrides"][0]["after_value"] == "1050.00"

        # Maker attempting to self-approve must fail with 403.
        self_check = await client.post(
            f"/v1/approvals/{apr_id}/check",
            headers={"X-Dev-User": "alice-maker"},
            json={"decision": "approved", "note": "Self approve"},
        )
        assert self_check.status_code == 403
        assert "Four-eyes" in self_check.json()["detail"]

        # Checker returns to Maker, Maker resubmits, Checker approves.
        ret_res = await client.post(
            f"/v1/approvals/{apr_id}/check",
            headers={"X-Dev-User": "bob-checker"},
            json={"decision": "returned_to_maker", "note": "Verify supplier tax ID."},
        )
        assert ret_res.status_code == 200
        assert ret_res.json()["status"] == "returned_to_maker"

        resubmit = await client.post(
            f"/v1/approvals/{apr_id}/make",
            headers={"X-Dev-User": "alice-maker"},
            json={"overrides": [], "note": "Tax ID verified."},
        )
        assert resubmit.status_code == 200

        approve_res = await client.post(
            f"/v1/approvals/{apr_id}/check",
            headers={"X-Dev-User": "bob-checker"},
            json={"decision": "approved", "note": "Approved under four-eyes."},
        )
        assert approve_res.status_code == 200
        assert approve_res.json()["status"] == "approved"
        assert len(core_gateway.events) == 2
        assert core_gateway.events[-1].decision == "approved"
        assert core_gateway.events[-1].checker_sub == "bob-checker"

        # Verify cryptographic audit hash chain end-to-end.
        verify_res = await client.get("/v1/audit-events/verify")
        assert verify_res.status_code == 200
        assert verify_res.json() == {"valid": True, "checked_count": 6, "first_broken_id": None}
