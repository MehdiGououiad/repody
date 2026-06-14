from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SchemaFieldSpec:
    name: str
    description: str = ""


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
    ocr_model: str | None = None
    llm_model: str | None = None
    extraction_ms: int = 0
    combined_llm: bool = False
    cache_hit: bool = False
    gpu_cold_start_likely: bool = False
    fields_extracted: int = 0
    ocr_text: str | None = None
    ocr_skipped: bool = False


OCR_TEXT_MAX_CHARS = 80_000


def truncate_ocr_text(text: str | None, *, max_chars: int = OCR_TEXT_MAX_CHARS) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if "<table" in stripped.lower() or "<div" in stripped.lower():
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


class DocumentExtractor(ABC):
    @abstractmethod
    async def extract(
        self,
        document_bytes: bytes | None,
        mime_type: str,
        document_type: str,
        schema: list[SchemaFieldSpec],
        *,
        extraction_mode: str = "auto",
        ocr_model: str | None = None,
        storage_key: str | None = None,
        file_size: int | None = None,
        bundle: object | None = None,
        validation_mode: str = "logic_only",
        llm_rules: list[dict] | None = None,
        llm_model: str | None = None,
    ) -> ExtractionResult: ...
