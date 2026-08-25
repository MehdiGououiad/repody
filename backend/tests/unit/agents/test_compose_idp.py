"""IDP compose_idp — pure orchestration with injected ports."""

from __future__ import annotations

import pytest

from repody.agents.idp.compose import compose_idp
from repody.agents.idp.contracts import (
    DocumentExtraction,
    DocumentSpec,
    ExtractedField,
    ExtractionOutput,
    IdpExtractionMeta,
    IdpInput,
    IdpWorkflowConfig,
    RuleResult,
    RuleSpec,
    SchemaField,
    StoredDocument,
    ValidationOutput,
)
from repody.agents.idp.run import wrap_idp_outcome
from repody.runtime.contracts.agent import AgentStatus
from repody.runtime.contracts.result import ErrorCode, Result


def _stored(doc_id: str = "d1") -> StoredDocument:
    return StoredDocument(
        document_id=doc_id,
        storage_key=f"runs/{doc_id}/f.pdf",
        mime_type="application/pdf",
        size_bytes=10,
    )


def _spec(doc_id: str = "d1") -> DocumentSpec:
    return DocumentSpec(
        id=doc_id,
        label="Invoice",
        schema_fields=(SchemaField(name="total"),),
        document_model_id="repody:vlm",
        extraction_mode="document_model",
    )


def _extraction(doc_id: str = "d1") -> DocumentExtraction:
    return DocumentExtraction(
        document_id=doc_id,
        fields=(
            ExtractedField(
                key="total",
                value="100",
                field_type="number",
                extracted=True,
                confidence=0.9,
            ),
        ),
        markdown_text=None,
        meta=IdpExtractionMeta(
            read_path_config="document_model",
            read_path_used="document_model",
            validation_mode="logic_only",
            document_model_id="repody:vlm",
            cache_hit=False,
            extraction_ms=12,
            fields_extracted=1,
        ),
    )


def _input() -> IdpInput:
    return IdpInput(
        run_id="run-1",
        workflow=IdpWorkflowConfig(
            workflow_id="wf-1",
            documents=(_spec(),),
            rules=(
                RuleSpec(
                    id="r1",
                    name="Total present",
                    kind="logic",
                    scope="intra",
                    severity="reject",
                    applies_to=(),
                    body="total != None",
                ),
            ),
        ),
        documents=(_stored(),),
    )


@pytest.mark.asyncio
async def test_compose_idp_extracts_and_validates() -> None:
    async def fetch_bytes(_key: str) -> bytes:
        return b"%PDF"

    async def extract_one(spec, stored, blob):
        assert blob == b"%PDF"
        assert stored.document_id == spec.id
        return Result.ok(_extraction(spec.id))

    async def validate(extraction: ExtractionOutput) -> ValidationOutput:
        assert len(extraction.by_document) == 1
        return ValidationOutput(
            rule_results=(
                RuleResult(
                    rule_id="r1",
                    name="Total present",
                    status="passed",
                    severity="reject",
                    detail="ok",
                    affected_fields=("total",),
                ),
            ),
            overall_status="passed",
            summary_passed=1,
            summary_failed=0,
        )

    result = await compose_idp(
        _input(),
        fetch_bytes=fetch_bytes,
        extract_one=extract_one,
        validate=validate,
    )
    assert result.is_ok
    outcome = result.unwrap()
    assert outcome.run_id == "run-1"
    assert outcome.validation.overall_status == "passed"
    assert outcome.errors == ()


@pytest.mark.asyncio
async def test_compose_idp_soft_fails_document_load() -> None:
    async def fetch_bytes(_key: str) -> bytes:
        raise OSError("missing object")

    async def extract_one(*_args):
        raise AssertionError("extract should not run")

    async def validate(extraction: ExtractionOutput) -> ValidationOutput:
        assert extraction.by_document == ()
        return ValidationOutput(
            rule_results=(),
            overall_status="passed",
            summary_passed=0,
            summary_failed=0,
        )

    result = await compose_idp(
        _input(),
        fetch_bytes=fetch_bytes,
        extract_one=extract_one,
        validate=validate,
    )
    assert result.is_ok
    outcome = result.unwrap()
    assert len(outcome.errors) == 1
    assert outcome.errors[0].code is ErrorCode.INFRA


@pytest.mark.asyncio
async def test_wrap_idp_outcome_from_compose() -> None:
    async def fetch_bytes(_key: str) -> bytes:
        return b"x"

    async def extract_one(spec, stored, blob):
        return Result.ok(_extraction(spec.id))

    async def validate(extraction: ExtractionOutput) -> ValidationOutput:
        return ValidationOutput(
            rule_results=(),
            overall_status="passed",
            summary_passed=0,
            summary_failed=0,
        )

    result = await compose_idp(
        _input(),
        fetch_bytes=fetch_bytes,
        extract_one=extract_one,
        validate=validate,
    )
    assert result.is_ok
    agent = wrap_idp_outcome(result.unwrap())
    assert agent.status is AgentStatus.PASSED
