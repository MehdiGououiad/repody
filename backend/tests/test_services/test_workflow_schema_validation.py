import pytest

from audit_workbench.schemas.workflow import DocumentDefSchema, SchemaFieldSchema, WorkflowSchema
from audit_workbench.services.workflow import (
    duplicate_field_names,
    validate_workflow_schema,
)


def test_duplicate_field_names_case_insensitive():
    fields = [
        SchemaFieldSchema(id="1", name="Invoice_Number", description=""),
        SchemaFieldSchema(id="2", name="invoice_number", description=""),
    ]
    assert duplicate_field_names(fields) == ["invoice_number"]


def test_validate_workflow_schema_blocks_duplicates():
    payload = WorkflowSchema(
        id="wf-test",
        name="Test",
        documents=[
            DocumentDefSchema(
                id="doc-1",
                document_type="Invoice",
                schema_fields=[
                    SchemaFieldSchema(id="a", name="total", description=""),
                    SchemaFieldSchema(id="b", name="Total", description=""),
                ],
            )
        ],
    )
    with pytest.raises(ValueError, match="duplicate field name"):
        validate_workflow_schema(payload)


def test_validate_workflow_schema_rejects_unknown_document_model():
    payload = WorkflowSchema(
        id="wf-test",
        name="Test",
        documents=[
            DocumentDefSchema(
                id="doc-1",
                document_type="Invoice",
                document_model_id="not-a-real-model",
                schema_fields=[
                    SchemaFieldSchema(id="a", name="total", description=""),
                ],
            )
        ],
    )
    with pytest.raises(ValueError, match="not-a-real-model"):
        validate_workflow_schema(payload)
