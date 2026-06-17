"""Pydantic models for structured LLM outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LlmRuleVerdict(BaseModel):
    passed: bool
    detail: str = ""


class LlmRuleBatchRow(BaseModel):
    id: str
    passed: bool
    detail: str = ""


class LlmRuleBatchOutput(BaseModel):
    results: list[LlmRuleBatchRow] = Field(default_factory=list)
