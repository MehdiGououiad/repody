"""Tests for durable pipeline API gating, orchestration, and Hatchet child stubs."""

from typing import Any

from hatchet_sdk import DesiredWorkerLabel
from httpx import ASGITransport, AsyncClient

from repody_common.contracts import (
    CaseRef,
    FraudPostVerifyInput,
    FraudPostVerifyOutput,
    FraudPreCheckInput,
    FraudPreCheckOutput,
    IdpStageInput,
    IdpStageOutput,
)
from repody_core.api.deps import get_dispatcher, get_entitlement_provider, get_store
from repody_core.app.pipelines import execute_pipeline_stages
from repody_core.infra.queue import (
    FRAUD_POST_VERIFY_TASK,
    FRAUD_PRE_CHECK_TASK,
    IDP_STAGE_TASK,
    HatchetStageInvoker,
)
from repody_core.main import create_app
from repody_core.schemas.pipelines import (
    FourEyesGateStage,
    FraudPostVerifyStage,
    FraudPreCheckStage,
    IdpPipelineStage,
    PipelineTaskInput,
)


async def test_pipeline_api_enforces_entitlements_and_audits(
    core_store: Any,
    core_gateway: Any,
    entitlement_factory: Any,
) -> None:
    idp_only = entitlement_factory(("idp",))

    app = create_app()
    app.dependency_overrides[get_store] = lambda: core_store
    app.dependency_overrides[get_dispatcher] = lambda: core_gateway
    app.dependency_overrides[get_entitlement_provider] = lambda: idp_only

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        case_res = await client.post(
            "/v1/cases",
            headers={"X-Dev-User": "alice-maker"},
            json={"account_id": "acc-atlas", "external_ref": "CASE-100"},
        )
        assert case_res.status_code == 201
        case_id = case_res.json()["id"]

        # Unlicensed fraud stage must fail with 403 before dispatch.
        denied = await client.post(
            f"/v1/cases/{case_id}/pipelines",
            headers={"X-Dev-User": "alice-maker"},
            json={"stages": [{"kind": "fraud_pre_check"}]},
        )
        assert denied.status_code == 403
        assert "fraud" in denied.json()["detail"].lower()
        assert core_gateway.dispatched == []

        # Licensed IDP stage dispatches cleanly and records hash-chained audit event.
        started = await client.post(
            f"/v1/cases/{case_id}/pipelines",
            headers={"X-Dev-User": "alice-maker"},
            json={"stages": [{"kind": "idp", "workflow_id": "wf-invoices"}]},
        )
        assert started.status_code == 202
        body = started.json()
        assert body["case_id"] == case_id
        assert body["hatchet_run_id"] == "hatchet-1"
        assert len(core_gateway.dispatched) == 1
        assert core_gateway.dispatched[0].pipeline_run_id == body["id"]

        fetched = await client.get(f"/v1/pipelines/{body['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == body["id"]

        # Account scoping prevents cross-tenant pipeline reads.
        scoped_missing = await core_store.get_pipeline_run(body["id"], account="acc-other")
        assert scoped_missing is None

        verify_res = await client.get("/v1/audit-events/verify")
        assert verify_res.status_code == 200
        assert verify_res.json()["valid"] is True


class _FakeStageInvoker:
    def __init__(self, *, critical_pre_check: bool = False) -> None:
        self.calls: list[str] = []
        self.post_verify_inputs: list[FraudPostVerifyInput] = []
        self._critical = critical_pre_check

    async def run_fraud_pre_check(self, payload: FraudPreCheckInput) -> FraudPreCheckOutput:
        self.calls.append("fraud_pre_check")
        return FraudPreCheckOutput(
            analysis_id="frd-pre-1",
            risk_score=95 if self._critical else 5,
            severity="critical" if self._critical else "clean",
            short_circuit_recommended=self._critical,
        )

    async def run_idp(self, payload: IdpStageInput) -> IdpStageOutput:
        self.calls.append("idp")
        return IdpStageOutput(
            idp_run_id="run-idp-1",
            outcome="passed",
            extracted_data={"Invoice": {"total": 100}},
            pages_processed=1,
        )

    async def run_fraud_post_verify(self, payload: FraudPostVerifyInput) -> FraudPostVerifyOutput:
        self.calls.append("fraud_post_verify")
        self.post_verify_inputs.append(payload)
        return FraudPostVerifyOutput(
            analysis_id="frd-post-1",
            risk_score=10,
            severity="low",
            requires_four_eyes=True,
        )


async def test_execute_pipeline_short_circuits_on_critical_fraud() -> None:
    invoker = _FakeStageInvoker(critical_pre_check=True)
    waits: list[str] = []

    async def wait_for_approval(approval_id: str) -> dict[str, Any]:
        waits.append(approval_id)
        return {"decision": "approved"}

    result = await execute_pipeline_stages(
        PipelineTaskInput(
            pipeline_run_id="pipe-1",
            case=CaseRef(case_id="case-1"),
            stages=[
                FraudPreCheckStage(short_circuit_on_critical=True),
                IdpPipelineStage(workflow_id="wf-1"),
                FraudPostVerifyStage(),
                FourEyesGateStage(approval_id="apr-1"),
            ],
        ),
        invoker=invoker,
        wait_for_approval=wait_for_approval,
    )
    assert result["status"] == "short_circuited"
    assert invoker.calls == ["fraud_pre_check"]
    assert waits == []


async def test_execute_pipeline_chains_data_across_all_stages() -> None:
    invoker = _FakeStageInvoker(critical_pre_check=False)
    waits: list[str] = []

    async def wait_for_approval(approval_id: str) -> dict[str, Any]:
        waits.append(approval_id)
        return {"decision": "approved"}

    result = await execute_pipeline_stages(
        PipelineTaskInput(
            pipeline_run_id="pipe-2",
            case=CaseRef(case_id="case-2"),
            stages=[
                FraudPreCheckStage(),
                IdpPipelineStage(workflow_id="wf-1"),
                FraudPostVerifyStage(),
                FourEyesGateStage(approval_id="apr-2"),
            ],
        ),
        invoker=invoker,
        wait_for_approval=wait_for_approval,
    )
    assert result["status"] == "completed"
    assert invoker.calls == ["fraud_pre_check", "idp", "fraud_post_verify"]
    assert waits == ["apr-2"]
    assert invoker.post_verify_inputs[0].pre_check_analysis_id == "frd-pre-1"
    assert invoker.post_verify_inputs[0].extracted_data == {"Invoice": {"total": 100}}


class _FakeStub:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[Any, list[DesiredWorkerLabel] | None]] = []

    async def aio_run(
        self,
        payload: Any,
        *,
        wait_for_result: bool = True,
        desired_worker_labels: list[DesiredWorkerLabel] | None = None,
    ) -> Any:
        assert wait_for_result is True
        self.calls.append((payload, desired_worker_labels))
        if self.name == IDP_STAGE_TASK:
            return IdpStageOutput(idp_run_id="run-1", outcome="passed")
        if self.name == FRAUD_PRE_CHECK_TASK:
            return FraudPreCheckOutput(analysis_id="pre-1", risk_score=0, severity="clean")
        return FraudPostVerifyOutput(
            analysis_id="post-1",
            risk_score=0,
            severity="clean",
            requires_four_eyes=False,
        )


class _FakeStubsClient:
    def __init__(self) -> None:
        self.registered: dict[str, _FakeStub] = {}

    def task(self, *, name: str, **_kwargs: Any) -> _FakeStub:
        stub = _FakeStub(name)
        self.registered[name] = stub
        return stub


class _FakeHatchet:
    def __init__(self) -> None:
        self.stubs = _FakeStubsClient()


async def test_hatchet_stage_invoker_routes_to_expected_pools() -> None:
    fake = _FakeHatchet()
    invoker = HatchetStageInvoker(fake)  # type: ignore[arg-type]

    case = CaseRef(case_id="case-pool")
    await invoker.run_fraud_pre_check(FraudPreCheckInput(case=case, artifacts=[]))
    await invoker.run_idp(IdpStageInput(case=case, workflow_id="wf-1", artifacts=[]))
    await invoker.run_fraud_post_verify(FraudPostVerifyInput(case=case, artifacts=[]))

    assert set(fake.stubs.registered) == {
        IDP_STAGE_TASK,
        FRAUD_PRE_CHECK_TASK,
        FRAUD_POST_VERIFY_TASK,
    }
    assert fake.stubs.registered[IDP_STAGE_TASK].calls[0][1][0].value == "idp"  # type: ignore[index]
    assert fake.stubs.registered[FRAUD_PRE_CHECK_TASK].calls[0][1][0].value == "fraud-cpu"  # type: ignore[index]
    assert fake.stubs.registered[FRAUD_POST_VERIFY_TASK].calls[0][1][0].value == "fraud-gpu"  # type: ignore[index]
