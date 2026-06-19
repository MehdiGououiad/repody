from __future__ import annotations

import hashlib
import json

import structlog

from audit_workbench.extraction.base import (
    ExtractedFieldResult,
    ExtractionResult,
    SchemaFieldSpec,
    truncate_ocr_text,
)
from audit_workbench.services.redis_pool import get_redis
from audit_workbench.settings import get_settings

log = structlog.get_logger()

CACHE_VERSION = "v6"


async def _redis_client():
    settings = get_settings()
    if not settings.extraction_cache_enabled:
        return None
    return await get_redis()


def schema_fingerprint(schema: list[SchemaFieldSpec]) -> str:
    """Fingerprint field names and extraction prompts (descriptions) in schema order."""
    parts: list[str] = []
    for field in schema:
        name = field.name.strip().lower().replace(" ", "_")
        if not name:
            continue
        description = (field.description or "").strip()
        template_type = (field.template_type or "").strip()
        parts.append(f"{name}\x1f{description}\x1f{template_type}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def cache_key(
    *,
    content_hash: str,
    schema_fp: str,
    extraction_mode: str,
    ocr_model: str | None,
    extractor: str,
) -> str:
    model_part = ocr_model or "default"
    return (
        f"extract:{CACHE_VERSION}:{extractor}:{extraction_mode}:"
        f"{model_part}:{schema_fp}:{content_hash}"
    )


def cache_key_from_storage(
    *,
    storage_key: str,
    file_size: int,
    content_hash: str,
    schema_fp: str,
    extraction_mode: str,
    ocr_model: str | None,
    extractor: str,
) -> str:
    """Cache lookup keyed by storage path, size, and content hash."""
    model_part = ocr_model or "default"
    safe_key = storage_key.replace(":", "_")
    return (
        f"extract:{CACHE_VERSION}s:{extractor}:{extraction_mode}:{model_part}:"
        f"{schema_fp}:{content_hash}:{safe_key}:{file_size}"
    )


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def should_cache_result(result: ExtractionResult) -> bool:
    """Do not cache stub fallbacks or zero-field extractions."""
    if result.raw_text and str(result.raw_text).startswith("stub_fallback:"):
        return False
    if sum(1 for f in result.fields if f.extracted) == 0:
        return False
    return True


def _serialize_result(result: ExtractionResult) -> str:
    llm_rules: dict[str, list] = {}
    if result.llm_rule_results:
        llm_rules = {
            rid: [status, detail] for rid, (status, detail) in result.llm_rule_results.items()
        }
    payload = {
        "rawText": truncate_ocr_text(result.raw_text),
        "ocrText": truncate_ocr_text(result.ocr_text),
        "readPathUsed": result.read_path_used,
        "llmRuleResults": llm_rules,
        "fields": [
            {
                "key": f.key,
                "description": f.description,
                "value": f.value,
                "type": f.type,
                "confidence": f.confidence,
                "extracted": f.extracted,
            }
            for f in result.fields
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _deserialize_result(raw: str) -> ExtractionResult:
    data = json.loads(raw)
    fields = [
        ExtractedFieldResult(
            key=row["key"],
            description=row.get("description") or "",
            value=row.get("value") or "—",
            type=row.get("type") or "string",
            confidence=row.get("confidence"),
            extracted=bool(row.get("extracted")),
        )
        for row in data.get("fields", [])
    ]
    llm_raw = data.get("llmRuleResults") or {}
    llm_rule_results: dict[str, tuple[str, str]] = {}
    if isinstance(llm_raw, dict):
        for rid, pair in llm_raw.items():
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                llm_rule_results[str(rid)] = (str(pair[0]), str(pair[1]))
    return ExtractionResult(
        fields=fields,
        raw_text=data.get("rawText"),
        ocr_text=data.get("ocrText"),
        read_path_used=data.get("readPathUsed"),
        llm_rule_results=llm_rule_results or None,
    )


async def get_cached(key: str) -> ExtractionResult | None:
    client = await _redis_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        if not raw:
            return None
        log.info("extraction_cache_hit", key=key[:48])
        return _deserialize_result(raw)
    except Exception as exc:
        log.warning("extraction_cache_get_failed", error=repr(exc))
        return None


async def set_cached(key: str, result: ExtractionResult) -> None:
    if not should_cache_result(result):
        return
    client = await _redis_client()
    if client is None:
        return
    settings = get_settings()
    try:
        await client.setex(key, settings.extraction_cache_ttl_seconds, _serialize_result(result))
    except Exception as exc:
        log.warning("extraction_cache_set_failed", error=repr(exc))
