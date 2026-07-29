"""Extraction result types (data only — no extractor ABC)."""

from __future__ import annotations

from dataclasses import dataclass

from repody.extraction.modes import DEFAULT_READ_PATH_ID

__all__ = [
    "DEFAULT_READ_PATH_ID",
    "DocumentBundle",
    "ExtractionIclExample",
    "ExtractionMetadata",
    "ExtractionResult",
    "ExtractedFieldResult",
    "MARKDOWN_TEXT_MAX_CHARS",
    "SchemaFieldSpec",
    "load_document_bundle",
    "truncate_text",
]


@dataclass
class DocumentBundle:
    """In-memory document bytes for NuExtract vision extraction."""

    raw_bytes: bytes
    mime_type: str
    page_count: int = 0


def load_document_bundle(
    document_bytes: bytes,
    mime_type: str,
    *,
    settings: object | None = None,
) -> DocumentBundle:
    """Wrap uploaded bytes; page count is set when pages are rendered for VLM."""
    _ = settings
    mime = (mime_type or "").lower()
    return DocumentBundle(raw_bytes=document_bytes, mime_type=mime_type or mime)


@dataclass
class SchemaFieldSpec:
    name: str
    description: str = ""
    template_type: str | None = None
    enum_values: list[str] | None = None
    children: list[SchemaFieldSpec] | None = None


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

    read_path_config: str
    read_path_used: str
    read_path_label: str
    validation_mode: str
    validation_label: str
    document_model_id: str | None = None
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
    llm_rule_results: dict[str, tuple[str, str]] | None = None
    read_path_used: str | None = None
    meta: ExtractionMetadata | None = None
    pages_rendered: int | None = None
    pages_sent: int | None = None
    pages_dropped: int | None = None
