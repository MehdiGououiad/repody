from types import SimpleNamespace

from repody.app.workflow.mappers import _schema_field_from_orm
from repody.app.workflow.repository import _schema_field_columns
from repody.schemas.workflow import SchemaFieldSchema


def test_nested_object_fields_survive_save_and_load():
    field = SchemaFieldSchema.model_validate(
        {
            "id": "f1",
            "name": "party",
            "templateType": "object",
            "children": [
                {
                    "id": "c1",
                    "name": "address",
                    "templateType": "object",
                    "children": [{"id": "c2", "name": "city"}],
                },
                {
                    "id": "c3",
                    "name": "role",
                    "templateType": "enum",
                    "enumValues": ["buyer", "seller"],
                },
            ],
        }
    )

    template_type, config = _schema_field_columns(field)
    loaded = _schema_field_from_orm(
        SimpleNamespace(
            id="f1", name="party", description="", template_type=template_type, field_config=config
        )
    )

    assert loaded.children[0].children[0].name == "city"
    assert loaded.children[1].enum_values == ["buyer", "seller"]


def test_children_imply_an_object_group():
    field = SchemaFieldSchema.model_validate(
        {"id": "f1", "name": "party", "children": [{"id": "c1", "name": "city"}]}
    )
    assert _schema_field_columns(field)[0] == "object"
