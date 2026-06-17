from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import (
    Document,
    ExtractedField,
    RuleResult,
    RuleTemplate,
    Run,
    RunDocument,
    RunStatus,
    SchemaField,
    Workflow,
    WorkflowRule,
    WorkflowStatus,
)
from audit_workbench.services.api_keys import api_key_hint, hash_api_key

RULE_TEMPLATES = [
    RuleTemplate(
        id="tpl-sum-check",
        name="Sum check",
        kind="logic",
        scope="intra",
        description="Verify part_a + part_b equals total.",
        body="part_a + part_b == total",
        severity="reject",
    ),
    RuleTemplate(
        id="tpl-cross-match",
        name="Cross-document match",
        kind="logic",
        scope="cross",
        description="A field must match across two documents.",
        body="doc_a.reference == doc_b.reference",
        severity="reject",
    ),
    RuleTemplate(
        id="tpl-llm-review",
        name="LLM policy review",
        kind="llm",
        scope="intra",
        description="Natural-language check against extracted fields.",
        body="Review the extracted fields and fail if any required clause or value is missing or inconsistent.",
        severity="flag",
    ),
]


SEED_WORKFLOW_ID = "wf-invoice-audit"
SEED_API_KEY = "wbk_live_4f8a2c1e9d3b7f6a0c5e2d8b1a4f7c3e"


async def seed_database(session: AsyncSession) -> None:
    for tpl in RULE_TEMPLATES:
        if not await session.get(RuleTemplate, tpl.id):
            session.add(
                RuleTemplate(
                    id=tpl.id,
                    name=tpl.name,
                    kind=tpl.kind,
                    scope=tpl.scope,
                    description=tpl.description,
                    body=tpl.body,
                    severity=tpl.severity,
                )
            )
    await session.flush()

    existing = await session.execute(select(Workflow).where(Workflow.id == "wf-invoice-audit"))
    seeded = existing.scalar_one_or_none()
    if seeded:
        if seeded.status == WorkflowStatus.archived.value:
            seeded.status = WorkflowStatus.active.value
        return

    wf = Workflow(
        id=SEED_WORKFLOW_ID,
        name="Invoice Audit Pipeline",
        description="Multi-vendor invoice extraction with math and cross-reference checks.",
        status=WorkflowStatus.active.value,
        owner="Mehdi A.",
        deployed_at=datetime(2023, 10, 12, tzinfo=UTC),
        api_key=hash_api_key(SEED_API_KEY),
        api_key_hint=api_key_hint(SEED_API_KEY),
    )
    session.add(wf)

    doc_inv = Document(id="doc-invoice", workflow_id=wf.id, document_type="Invoice", position=0)
    doc_po = Document(id="doc-po", workflow_id=wf.id, document_type="Purchase Order", position=1)
    session.add_all([doc_inv, doc_po])

    inv_fields = [
        ("f1", "invoice_number", "Unique identifier, usually near the header."),
        ("f2", "vendor_name", "Legal name of the vendor issuing the invoice."),
        ("f3", "subtotal", "Sum of line items before tax."),
        ("f4", "tax", "Total tax amount applied."),
        ("f5", "total_amount", "Final amount due, including taxes and fees."),
        ("f6", "po_number", "Purchase order number referenced on the invoice."),
    ]
    for i, (fid, name, desc) in enumerate(inv_fields):
        session.add(
            SchemaField(id=fid, document_id=doc_inv.id, name=name, description=desc, position=i)
        )

    po_fields = [
        ("p1", "po_number", "Unique purchase order identifier."),
        ("p2", "approved_total", "Approved total amount on the PO."),
        ("p3", "vendor_name", "Vendor name as listed on the purchase order."),
    ]
    for i, (fid, name, desc) in enumerate(po_fields):
        session.add(
            SchemaField(id=fid, document_id=doc_po.id, name=name, description=desc, position=i)
        )

    rules = [
        WorkflowRule(
            id="r-math",
            workflow_id=wf.id,
            name="Math integrity",
            kind="logic",
            scope="intra",
            body="subtotal + tax == total_amount",
            severity="reject",
            applies_to=["doc-invoice"],
            conditions=[
                {
                    "id": "c1",
                    "left": {"kind": "field", "value": "subtotal"},
                    "arithmeticOp": "+",
                    "leftExtra": {"kind": "field", "value": "tax"},
                    "operator": "==",
                    "right": {"kind": "field", "value": "total_amount"},
                }
            ],
            condition_junction="AND",
            position=0,
        ),
        WorkflowRule(
            id="r-fees",
            workflow_id=wf.id,
            name="Hidden late fees",
            kind="llm",
            scope="intra",
            body="Flag if the invoice contains late fees or penalty charges hidden in line item descriptions.",
            severity="flag",
            applies_to=["doc-invoice"],
            position=1,
        ),
    ]
    session.add_all(rules)

    run = Run(
        id="AUD-2023-8902",
        workflow_id=wf.id,
        source="api",
        status=RunStatus.done.value,
        overall_status="failed",
        summary_total=2,
        summary_passed=1,
        summary_failed=1,
        fields_extracted=6,
        created_at=datetime(2023, 10, 24, 14, 32, tzinfo=UTC),
        finished_at=datetime(2023, 10, 24, 14, 32, 5, tzinfo=UTC),
    )
    session.add(run)
    rdoc = RunDocument(
        id="rdoc-seed", run_id=run.id, document_id=doc_inv.id, document_type="Invoice"
    )
    session.add(rdoc)
    await session.flush()

    seed_fields = [
        ("vendor_name", "Acme Corp Ltd.", False),
        ("subtotal", "5625.00", True),
        ("tax", "478.13", True),
        ("total_amount", "6200.00", True),
    ]
    for key, value, flagged in seed_fields:
        session.add(
            ExtractedField(
                id=f"fld-{key}",
                run_document_id=rdoc.id,
                key=key,
                description=key,
                value=value,
                type="currency" if key != "vendor_name" else "string",
                confidence=0.95,
                extracted=True,
                flagged=flagged,
            )
        )

    session.add_all(
        [
            RuleResult(
                id="rr-math",
                run_id=run.id,
                rule_id="r-math",
                name="Math integrity",
                kind="logic",
                scope="intra",
                status="failed",
                severity="reject",
                expression="subtotal + tax == total_amount",
                affected_fields=["subtotal", "tax", "total_amount"],
                detail="subtotal ($5,625.00) + tax ($478.13) = $6,103.13 ≠ total_amount ($6,200.00).",
                expected_value="$6,103.13",
                actual_value="$6,200.00",
            ),
            RuleResult(
                id="rr-fees",
                run_id=run.id,
                rule_id="r-fees",
                name="Hidden late fees",
                kind="llm",
                scope="intra",
                status="passed",
                severity="flag",
                expression="Flag hidden fees",
                affected_fields=[],
                detail="LLM evaluator scanned all line items and found no hidden fees.",
            ),
        ]
    )

    await session.flush()
