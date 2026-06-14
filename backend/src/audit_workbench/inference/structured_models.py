"""Pydantic models for structured LLM outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedFieldRow(BaseModel):
    name: str
    value: str = "—"
    confidence: float | None = None


class FieldExtractionOutput(BaseModel):
    fields: list[ExtractedFieldRow] = Field(default_factory=list)


class LlmRuleVerdict(BaseModel):
    passed: bool
    detail: str = ""


class LlmRuleBatchRow(BaseModel):
    id: str
    passed: bool
    detail: str = ""


class LlmRuleBatchOutput(BaseModel):
    results: list[LlmRuleBatchRow] = Field(default_factory=list)


class CombinedExtractionOutput(BaseModel):
    fields: list[ExtractedFieldRow] = Field(default_factory=list)
    rule_results: list[LlmRuleBatchRow] = Field(default_factory=list)
