"""Rules library API schemas."""

from __future__ import annotations

from pydantic import Field

from repody.schemas.common import CamelModel
from repody.schemas.workflow import RuleTemplateSchema


class RuleLibraryResponse(CamelModel):
    rules: list[RuleTemplateSchema] = Field(default_factory=list)
