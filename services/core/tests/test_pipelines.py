"""Tests for durable pipeline API gating, orchestration, and Hatchet child stubs."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from hatchet_sdk import DesiredWorkerLabel
from httpx import ASGITransport, AsyncClient

from repody_common.contracts import (
    CaseRef,
    FourEyesDecision,
    FraudPostVerifyInput,
    FraudPostVerifyOutput,
    FraudPreCheckInput,
    FraudPreCheckOutput,
    IdpStageInput,
    IdpStageOutput,
)
from repody_common.entitlements import (
    EntitlementState,
    LicenseClaims,
    ModuleId,
    sign_license_token,
    verify_license_token,
)
from repody_common.ids import new_id
from repody_core.api.deps import get_dispatcher, get_entitlement_provider, get_store
from repody_core.app.pipelines import execute_pipeline_stages
from repody_core.infra.queue import (
    FRAUD_POST_VERIFY_TASK,
    FRAUD_PRE_CHECK_TASK,
    IDP_STAGE_TASK,
    HatchetStageInvoker,
)
from repody_core.main import create_app
from repody_core.schemas.approvals import ApprovalStatus, ApprovalTaskResponse, FieldOverrideInput
from repody_core.schemas.audit import AuditEventResponse
from repody_core.schemas.cases import CaseResponse, CaseStatus, CreateCaseRequest
from repody_core.schemas.hashing import GENESIS_HASH, compute_event_hash
from repody_core.schemas.pipelines import (
    FourEyesGateStage,
    FraudPostVerifyStage,
    FraudPreCheckStage,
    IdpPipelineStage,
    PipelineRunResponse,
    PipelineTaskInput,
)


class _PipelineTestStore:
    """Minimal self-contained in-memory ``CoreStore`` for pipeline API tests."""

    def __init__(self) -> None:
        self.cases: dict[str, CaseResponse] = {}
        self.pipelines: dict[str, PipelineRunResponse] = {}
        self.events: list[AuditEventResponse] = []

    def _append(
        self,
        *,
        actor_sub: str,
        account_id: str | None,
        module: str,
        action: str,
        resource_id: str,
        detail: dict[str, Any],
    ) -> None:
        prev_hash = self.events[-1].event_hash if self.events else GENESIS_HASH
        event_id = new_id("evt")
        now = datetime.now(UTC)
        event_hash = compute_event_hash(
            prev_hash,
            event_id=event_id,
            actor_sub=actor_sub,
            account_id=account_id,
            module=module,
            action=action,
            resource_id=resource_id,
            detail=detail,
            created_at_iso=now.isoformat(),
        )
        self.events.append(
            AuditEventResponse(
                seq=len(self.events) + 1,
                id=event_id,
                actor_sub=actor_sub,
                account_id=account_id,
                module=module,
                action=action,
                resource_id=resource_id,
                detail=detail,
                prev_hash=prev_hash,
                event_hash=event_hash,
                created_at=now,
            )
        )

    async def create_case(
        self,
        *,
        case_id: str,
        actor_sub: str,
        request: CreateCaseRequest,
    ) -> CaseResponse:
        now = datetime.now(UTC)
        case = CaseResponse(
            id=case_id,
            account_id=request.account_id,
            external_ref=request.external_ref,
            input_payload=deepcopy(request.input_payload),
            status="open",
            created_by=actor_sub,
            created_at=now,
            updated_at=now,
            artifacts=[],
        )
        self.cases[case_id] = case
        self._append(
            actor_sub=actor_sub,
            account_id=request.account_id,
            module="core",
            action="case.created",
            resource_id=case_id,
            detail={"artifact_count": len(request.artifacts)},
        )
        return case

    async def get_case(self, case_id: str, *, account: str | None) -> CaseResponse | None:
        case = self.cases.get(case_id)
        if case is None or (account is not None and case.account_id != account):
            return None
        return case

    async def create_pipeline_run(
        self,
        *,
        pipeline_id: str,
        case_id: str,
        stages: list[dict[str, Any]],
        actor_sub: str,
        account_id: str | None,
    ) -> PipelineRunResponse:
        now = datetime.now(UTC)
        run = PipelineRunResponse(
            id=pipeline_id,
            case_id=case_id,
            stages=deepcopy(stages),
            status="queued",
            hatchet_run_id=None,
            created_at=now,
            finished_at=None,
        )
        self.pipelines[pipeline_id] = run
        self._append(
            actor_sub=actor_sub,
            account_id=account_id,
            module="core",
            action="pipeline.started",
            resource_id=pipeline_id,
            detail={"case_id": case_id, "stage_count": len(stages)},
        )
        return run

    async def set_pipeline_hatchet_run(
        self,
        *,
        pipeline_id: str,
        hatchet_run_id: str,
    ) -> PipelineRunResponse:
        updated = self.pipelines[pipeline_id].model_copy(update={"hatchet_run_id": hatchet_run_id})
        self.pipelines[pipeline_id] = updated
        return updated

    async def get_pipeline_run(
        self,
        pipeline_id: str,
        *,
        account: str | None,
    ) -> PipelineRunResponse | None:
        run = self.pipelines.get(pipeline_id)
        if run is None:
            return None
        case = self.cases.get(run.case_id)
        if account is not None and (case is None or case.account_id != account):
            return None
        return run

    async def create_approval(
        self,
        *,
        approval_id: str,
        case_id: str,
        stage_name: str,
        payload_snapshot: dict[str, Any],
        payload_sha256: str,
        actor_sub: str,
        account_id: str | None,
    ) -> ApprovalTaskResponse:
        raise NotImplementedError

    async def get_approval(self, approval_id: str) -> ApprovalTaskResponse | None:
        return None

    async def apply_maker_review(
        self,
        *,
        approval_id: str,
        maker_sub: str,
        next_status: ApprovalStatus,
        case_status: CaseStatus,
        updated_snapshot: dict[str, Any],
        payload_sha256: str,
        overrides: list[tuple[FieldOverrideInput, Any]],
        note: str,
        account_id: str | None,
    ) -> ApprovalTaskResponse:
        raise NotImplementedError

    async def apply_checker_decision(
        self,
        *,
        approval_id: str,
        checker_sub: str,
        decision: FourEyesDecision,
        next_status: ApprovalStatus,
        case_status: CaseStatus,
        note: str,
        account_id: str | None,
    ) -> ApprovalTaskResponse:
        raise NotImplementedError

    async def list_audit_events(
        self,
        *,
        account_id: str | None = None,
        limit: int = 200,
    ) -> list[AuditEventResponse]:
        items = [e for e in self.events if account_id is None or e.account_id == account_id]
        return items[:limit]


class _ConfigurableEntitlementProvider:
    """Offline Ed25519 entitlement provider parameterized by licensed modules."""

    def __init__(self, modules: tuple[ModuleId, ...]) -> None:
        key = Ed25519PrivateKey.generate()
        private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        self._public_pem = (
            key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )
        now = datetime.now(UTC)
        self._token = sign_license_token(
            LicenseClaims(
                customer_id="bank-atlas",
                modules=modules,
                issued_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=90),
            ),
            private_pem,
        )

    def current(self) -> EntitlementState:
        return verify_license_token(self._token, self._public_pem)


class _FakePipelineDispatcher:
    """Captures dispatched pipeline inputs without requiring a live Hatchet engine."""

    def __init__(self) -> None:
        self.dispatched: list[PipelineTaskInput] = []

    async def dispatch_pipeline(self, task_input: PipelineTaskInput) -> str | None:
        self.dispatched.append(task_input)
        return f"hatchet-{len(self.dispatched)}"


async def test_pipeline_api_enforces_entitlements_and_audits() -> None:
    store = _PipelineTestStore()
    dispatcher = _FakePipelineDispatcher()
    idp_only = _ConfigurableEntitlementProvider(("idp",))

    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_dispatcher] = lambda: dispatcher
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
        assert dispatcher.dispatched == []

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
        assert len(dispatcher.dispatched) == 1
        assert dispatcher.dispatched[0].pipeline_run_id == body["id"]

        fetched = await client.get(f"/v1/pipelines/{body['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == body["id"]

        # Account scoping prevents cross-tenant pipeline reads.
        scoped_missing = await store.get_pipeline_run(body["id"], account="acc-other")
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
