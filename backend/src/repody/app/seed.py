"""Demo data for development: one deployed invoice workflow and one finished audit."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.auth import api_key_hint, hash_api_key
from repody.infra.models import ExtractedField, RuleResult, Run, RunDocument, Workflow
from repody.schemas.rule import Condition, Operand, Rule
from repody.schemas.workflow import DocumentDef, SchemaField, WorkflowDefinition

SEED_WORKFLOW_ID = "wf-invoice-audit"
SEED_API_KEY = "wbk_live_4f8a2c1e9d3b7f6a0c5e2d8b1a4f7c3e"

_INVOICE_FIELDS = [
    ("f1", "invoice_number", "Unique identifier, usually near the header.", "verbatim-string"),
    ("f2", "vendor_name", "Legal name of the vendor issuing the invoice.", "verbatim-string"),
    ("f3", "subtotal", "Sum of line items before tax.", "number"),
    ("f4", "tax", "Total tax amount applied.", "number"),
    ("f5", "total_amount", "Final amount due, including taxes and fees.", "number"),
    ("f6", "po_number", "Purchase order number referenced on the invoice.", "verbatim-string"),
]
_PO_FIELDS = [
    ("p1", "po_number", "Unique purchase order identifier.", "verbatim-string"),
    ("p2", "approved_total", "Approved total amount on the PO.", "number"),
    ("p3", "vendor_name", "Vendor name as listed on the purchase order.", "verbatim-string"),
]
_MATH_RULE = Rule(
    id="r-math",
    name="Math integrity",
    applies_to=["doc-invoice"],
    conditions=[
        Condition(
            id="c1",
            left=Operand(kind="field", value="subtotal"),
            arithmetic_op="+",
            left_extra=Operand(kind="field", value="tax"),
            right=Operand(kind="field", value="total_amount"),
        )
    ],
)


def _fields(rows: list[tuple[str, str, str, str]]) -> list[SchemaField]:
    return [
        SchemaField(id=fid, name=name, description=desc, template_type=kind)
        for fid, name, desc, kind in rows
    ]


async def seed(session: AsyncSession) -> None:
    if await session.get(Workflow, SEED_WORKFLOW_ID) is not None:
        return
    definition = WorkflowDefinition(
        documents=[
            DocumentDef(id="doc-invoice", document_type="Invoice", schema=_fields(_INVOICE_FIELDS)),
            DocumentDef(id="doc-po", document_type="Purchase Order", schema=_fields(_PO_FIELDS)),
        ],
        rules=[_MATH_RULE],
    )
    session.add(
        Workflow(
            id=SEED_WORKFLOW_ID,
            name="Invoice Audit Pipeline",
            description="Multi-vendor invoice extraction with math and cross-reference checks.",
            status="active",
            owner="Demo",
            definition=definition.model_dump(),
            deployed_at=datetime(2023, 10, 12, tzinfo=UTC),
            api_key_hash=hash_api_key(SEED_API_KEY),
            api_key_hint=api_key_hint(SEED_API_KEY),
        )
    )
    await session.flush()
    finished = datetime(2023, 10, 24, 14, 32, 5, tzinfo=UTC)
    run = Run(
        id="AUD-2023-8902",
        workflow_id=SEED_WORKFLOW_ID,
        source="api",
        status="done",
        outcome="failed",
        definition=definition.model_dump(),
        rules_total=1,
        rules_failed=1,
        fields_extracted=4,
        created_at=datetime(2023, 10, 24, 14, 32, tzinfo=UTC),
        started_at=datetime(2023, 10, 24, 14, 32, tzinfo=UTC),
        finished_at=finished,
    )
    document = RunDocument(
        id="rdoc-seed",
        document_id="doc-invoice",
        document_type="Invoice",
        file_name="invoice.pdf",
        mime_type="application/pdf",
        storage_key="seed/invoice.pdf",
    )
    document.fields = [
        ExtractedField(
            id=f"fld-{key}",
            position=i,
            key=key,
            type=kind,
            value=value,
            flagged=key != "vendor_name",
        )
        for i, (key, kind, value) in enumerate(
            [
                ("vendor_name", "verbatim-string", "Acme Corp Ltd."),
                ("subtotal", "number", 5625.0),
                ("tax", "number", 478.13),
                ("total_amount", "number", 6200.0),
            ]
        )
    ]
    run.documents = [document]
    run.rule_results = [
        RuleResult(
            id="rr-math",
            rule_id="r-math",
            name="Math integrity",
            scope="intra",
            severity="reject",
            status="failed",
            expression="subtotal + tax == total_amount",
            detail="Not satisfied: subtotal + tax == total_amount",
            affected_fields=["subtotal", "tax", "total_amount"],
        )
    ]
    session.add(run)
