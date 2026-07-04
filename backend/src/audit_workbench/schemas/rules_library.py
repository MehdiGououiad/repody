"""Rules library API schemas."""

from __future__ import annotations

from pydantic import Field

from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.workflow import RuleTemplateSchema


class RuleLibraryResponse(CamelModel):
    rules: list[RuleTemplateSchema] = Field(default_factory=list)
