from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import (
    Document,
    ExtractedField,
    RuleResult,
    Run,
    RunDocument,
    RunStatus,
    SchemaField,
    Workflow,
    WorkflowRule,
    WorkflowStatus,
)
from audit_workbench.services.run_processor import process_run


@pytest.fixture
async def run_session(postgres_session):
    wf = Workflow(
        id="wf-test",
        name="Test",
        status=WorkflowStatus.active.value,
    )
    doc = Document(
        id="doc-1",
        workflow_id=wf.id,
        document_type="Invoice",
        position=0,
        extraction_mode="document_model",
    )
    field = SchemaField(
        id="sf-1",
        document_id=doc.id,
        name="total_amount",
        description="TTC",
        position=0,
    )
    rule = WorkflowRule(
        id="rule-1",
        workflow_id=wf.id,
        name="Math",
        kind="logic",
        scope="intra",
        body="total_amount == '6000.00'",
        severity="reject",
        position=0,
    )
    run = Run(
        id="run-test-1",
        workflow_id=wf.id,
        source="test",
        status=RunStatus.queued.value,
    )
    run_doc = RunDocument(
        id="rdoc-1",
        run_id=run.id,
        document_id=doc.id,
        document_type="Invoice",
    )
    postgres_session.add_all([wf, doc, field, rule, run, run_doc])
    await postgres_session.commit()
    yield postgres_session, run.id


@pytest.mark.asyncio
async def test_process_run_is_idempotent_when_already_running(run_session):
    session, run_id = run_session
    run = await session.get(Run, run_id)
    assert run is not None
    run.status = RunStatus.running.value
    await session.commit()

    await process_run(session, run_id)

    rr = await session.execute(select(RuleResult).where(RuleResult.run_id == run_id))
    ef = await session.execute(
        select(ExtractedField).join(RunDocument).where(RunDocument.run_id == run_id)
    )
    assert len(rr.scalars().all()) == 0
    assert len(ef.scalars().all()) == 0


@pytest.mark.asyncio
async def test_process_run_clears_prior_results_on_retry(run_session):
    session, run_id = run_session
    run_doc = (
        await session.execute(select(RunDocument).where(RunDocument.run_id == run_id))
    ).scalar_one()
    session.add(
        ExtractedField(
            id="fld-old",
            run_document_id=run_doc.id,
            key="total_amount",
            description="",
            value="999",
            type="currency",
            extracted=True,
        )
    )
    session.add(
        RuleResult(
            id="rr-old",
            run_id=run_id,
            rule_id="rule-1",
            name="Old",
            kind="logic",
            scope="intra",
            status="failed",
            severity="reject",
            expression="",
            affected_fields=[],
            detail="stale",
        )
    )
    await session.commit()

    run = await session.get(Run, run_id)
    assert run is not None
    run.status = RunStatus.queued.value
    await session.commit()

    await process_run(session, run_id)

    rr = (
        (await session.execute(select(RuleResult).where(RuleResult.run_id == run_id)))
        .scalars()
        .all()
    )
    assert all(r.id != "rr-old" for r in rr)

    result = await session.execute(
        select(Run)
        .where(Run.id == run_id)
        .options(selectinload(Run.documents).selectinload(RunDocument.fields))
    )
    claimed = result.scalar_one()
    field_ids = [f.id for rd in claimed.documents for f in rd.fields]
    assert "fld-old" not in field_ids
