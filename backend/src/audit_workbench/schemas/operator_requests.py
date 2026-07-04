"""Operator API request schemas."""

from __future__ import annotations

from pydantic import Field

from audit_workbench.schemas.common import CamelModel


class ModelActionRequest(CamelModel):
    model: str = Field(min_length=1, max_length=180)
