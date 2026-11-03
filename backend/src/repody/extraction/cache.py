from __future__ import annotations

import hashlib
import json

import structlog

from repody.extraction.types import (
    ExtractedFieldResult,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
    truncate_text,
)
from repody.infra.redis.pool import get_redis
from repody.rules.value_coercion import MISSING
from repody.settings import get_settings

log = structlog.get_logger()

CACHE_VERSION = "v23"


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
        parts.append(
            f"{name}\x1f{description}\x1f{template_type}\x1f{_field_config_fingerprint(field)}"
        )
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def _field_config_fingerprint(field: SchemaFieldSpec) -> str:
    chunks: list[str] = []
    if field.enum_values:
        chunks.append("enum:" + ",".join(field.enum_values))
    if field.children:
        for child in field.children:
            child_name = child.name.strip().lower()
            if not child_name:
                continue
            chunks.append(f"{child_name}:{child.template_type or ''}:{child.description.strip()}")
    return "|".join(chunks)


def cache_key(
    *,
    content_hash: str,
    schema: list[SchemaFieldSpec],
    served_model: str,
    markdown_extraction: bool,
    extraction_instructions: str,
    icl_examples: list[ExtractionIclExample] | None,
) -> str:
    """Same bytes + same request to the same model -> same key."""
    icl = "\n".join(
        f"{ex.input.strip()}\x1f{ex.output.strip()}"
        for ex in icl_examples or []
        if ex.input.strip()
    )
    request = "\x1e".join(
        [
            served_model.strip().lower(),
            "md" if markdown_extraction else "",
            extraction_instructions,
            icl,
        ]
    )
    request_fp = hashlib.sha256(request.encode()).hexdigest()[:16]
    return f"extract:{CACHE_VERSION}:{request_fp}:{schema_fingerprint(schema)}:{content_hash}"


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def should_cache_result(result: ExtractionResult) -> bool:
    """Cache field or text-only extractions."""
    if sum(1 for f in result.fields if f.extracted) > 0:
        return True
    text = (result.markdown_text or result.raw_text or "").strip()
    return len(text) > 0


def _serialize_result(result: ExtractionResult) -> str:
    payload = {
        "rawText": truncate_text(result.raw_text),
        "markdownText": truncate_text(result.markdown_text),
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
            value=row.get("value") or MISSING,
            type=row.get("type") or "string",
            confidence=row.get("confidence"),
            extracted=bool(row.get("extracted")),
        )
        for row in data.get("fields", [])
    ]
    return ExtractionResult(
        fields=fields,
        raw_text=data.get("rawText"),
        markdown_text=data.get("markdownText"),
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
