"""Extraction data types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from repody.util.json_shape import normalize_keys_to_snake

DEFAULT_TEMPLATE_TYPE = "verbatim-string"


class SchemaFieldSpec(BaseModel):
    """One workflow schema field, validated from any stored shape.

    Accepts ORM rows (``field_config`` holding ``enum_values`` / ``children``), snapshot
    JSON and API payloads, in camelCase or snake_case. ``template_type`` is a NuExtract
    TYPES.md leaf, a structure type (enum, multi-enum, object, object-array) or
    ``<leaf>-list``; it defaults to ``verbatim-string``.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str = ""
    template_type: str = DEFAULT_TEMPLATE_TYPE
    enum_values: list[str] | None = None
    children: list[SchemaFieldSpec] | None = None

    @model_validator(mode="before")
    @classmethod
    def _flatten_field_config(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = normalize_keys_to_snake(data)
        config = data.pop("field_config", None) or {}
        for key in ("enum_values", "children"):
            if data.get(key) is None and config.get(key) is not None:
                data[key] = config[key]
        return data

    @field_validator("name", "description", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("template_type", mode="before")
    @classmethod
    def _default_type(cls, value: Any) -> str:
        return str(value or "").strip() or DEFAULT_TEMPLATE_TYPE

    @field_validator("enum_values", mode="before")
    @classmethod
    def _clean_enum_values(cls, value: Any) -> list[str] | None:
        if not isinstance(value, list):
            return None
        cleaned = list(dict.fromkeys(str(v).strip() for v in value if str(v).strip()))
        return cleaned or None

    @field_validator("children", mode="before")
    @classmethod
    def _named_children(cls, value: Any) -> list[Any] | None:
        if not isinstance(value, list):
            return None
        named = [c for c in value if (c.get("name") if isinstance(c, dict) else c.name)]
        return named or None


@dataclass
class DocumentBundle:
    """Uploaded document bytes with their MIME type."""

    raw_bytes: bytes
    mime_type: str


@dataclass
class ExtractionIclExample:
    input: str
    output: str


@dataclass
class ExtractedFieldResult:
    key: str
    description: str
    value: str
    type: str
    confidence: float | None
    extracted: bool


@dataclass
class ExtractionMetadata:
    """Persisted on run documents and surfaced in audit reports."""

    extraction_ms: int = 0
    cache_hit: bool = False
    gpu_cold_start_likely: bool = False
    fields_extracted: int = 0
    markdown_extraction: bool = False
    markdown_text: str | None = None
    raw_text: str | None = None
    pages_rendered: int | None = None
    pages_sent: int | None = None
    pages_dropped: int | None = None


MARKDOWN_TEXT_MAX_CHARS = 80_000


def truncate_text(text: str | None, *, max_chars: int = MARKDOWN_TEXT_MAX_CHARS) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if len(stripped) <= max_chars:
        return stripped
    return f"{stripped[:max_chars]}\n\n… ({len(stripped) - max_chars:,} characters truncated)"


@dataclass
class ExtractionResult:
    fields: list[ExtractedFieldResult]
    raw_text: str | None = None
    markdown_text: str | None = None
    meta: ExtractionMetadata | None = None
    pages_rendered: int | None = None
    pages_sent: int | None = None
    pages_dropped: int | None = None
