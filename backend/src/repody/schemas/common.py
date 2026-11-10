from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        from_attributes=True,
        serialize_by_alias=True,
        json_schema_serialization_defaults_required=True,
    )


# What users type, trimmed and bounded (the database stores text of any length).
Name = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20_000)]
Id = Annotated[str, StringConstraints(max_length=64)]
