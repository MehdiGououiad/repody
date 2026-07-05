from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from audit_workbench.extraction.document_modes import DEFAULT_READ_PATH_ID


@dataclass
class SchemaFieldSpec:
    name: str
    description: str = ""
    template_type: str | None = None


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
    ocr_text: str | None = None
    raw_text: str | None = None
    ocr_skipped: bool = False
    pages_rendered: int | None = None
    pages_sent: int | None = None
    pages_dropped: int | None = None


OCR_TEXT_MAX_CHARS = 80_000


def truncate_text(text: str | None, *, max_chars: int = OCR_TEXT_MAX_CHARS) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if len(stripped) <= max_chars:
        return stripped
    return f"{stripped[:max_chars]}\n\n… ({len(stripped) - max_chars:,} characters truncated)"


def truncate_ocr_text(text: str | None, *, max_chars: int = OCR_TEXT_MAX_CHARS) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    from audit_workbench.extraction.ocr_markdown import normalize_ocr_markdown

    stripped = normalize_ocr_markdown(stripped) or stripped
    if len(stripped) <= max_chars:
        return stripped
    return f"{stripped[:max_chars]}\n\n… ({len(stripped) - max_chars:,} characters truncated)"


@dataclass
class ExtractionResult:
    fields: list[ExtractedFieldResult]
    raw_text: str | None = None
    ocr_text: str | None = None
    llm_rule_results: dict[str, tuple[str, str]] | None = None
    read_path_used: str | None = None
    ocr_skipped: bool = False
    meta: ExtractionMetadata | None = None
    pages_rendered: int | None = None
    pages_sent: int | None = None
    pages_dropped: int | None = None


class DocumentExtractor(ABC):
    @abstractmethod
    async def extract(
        self,
        document_bytes: bytes | None,
        mime_type: str,
        document_type: str,
        schema: list[SchemaFieldSpec],
        *,
        extraction_mode: str = DEFAULT_READ_PATH_ID,
        document_model_id: str | None = None,
        storage_key: str | None = None,
        file_size: int | None = None,
        bundle: object | None = None,
        validation_mode: str = "logic_only",
        extraction_instructions: str = "",
        markdown_extraction: bool = False,
    ) -> ExtractionResult: ...
