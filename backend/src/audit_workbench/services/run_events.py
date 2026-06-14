from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import structlog

from audit_workbench.services.redis_pool import get_redis
from audit_workbench.settings import get_settings

log = structlog.get_logger(__name__)

_SSE_HEARTBEAT_SECONDS = 30.0
_SSE_MAX_DURATION_SECONDS = 3600.0


def _channel(run_id: str) -> str:
    return f"audit:run:progress:{run_id}"


async def _redis_client():
    settings = get_settings()
    if not settings.run_events_enabled:
        return None
    return await get_redis()


def _is_terminal_payload(data: dict[str, Any]) -> bool:
    if data.get("terminal"):
        return True
    progress = data.get("progress")
    if isinstance(progress, dict) and progress.get("failed"):
        return True
    return False


def _parse_message(data: str | bytes) -> dict[str, Any] | None:
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


async def publish_run_progress(run_id: str, progress: dict[str, Any]) -> None:
    client = await _redis_client()
    if client is None:
        return
    payload = json.dumps({"runId": run_id, "progress": progress}, ensure_ascii=False)
    try:
        await client.publish(_channel(run_id), payload)
    except Exception as exc:
        log.warning(
            "run_progress_publish_failed",
            event_domain="run_events",
            run_id=run_id,
            error_type=type(exc).__name__,
            error_message=repr(exc),
        )


async def publish_run_terminal(run_id: str, *, status: str) -> None:
    """Signal SSE subscribers that the run reached a terminal state."""
    client = await _redis_client()
    if client is None:
        return
    payload = json.dumps(
        {"runId": run_id, "terminal": True, "status": status},
        ensure_ascii=False,
    )
    try:
        await client.publish(_channel(run_id), payload)
        log.info(
            "run_events_terminal_published",
            event_domain="run_events",
            run_id=run_id,
            run_status=status,
        )
    except Exception as exc:
        log.warning(
            "run_terminal_publish_failed",
            event_domain="run_events",
            run_id=run_id,
            error_type=type(exc).__name__,
            error_message=repr(exc),
        )


async def subscribe_run_progress(run_id: str) -> AsyncIterator[dict[str, Any]]:
    """Yield parsed progress event payloads until terminal or timeout."""
    client = await _redis_client()
    if client is None:
        yield {"disabled": True, "terminal": True}
        return

    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(run_id))
    started = time.monotonic()
    try:
        while True:
            elapsed = time.monotonic() - started
            if elapsed >= _SSE_MAX_DURATION_SECONDS:
                log.info(
                    "run_events_stream_timeout",
                    event_domain="run_events",
                    run_id=run_id,
                    duration_seconds=int(elapsed),
                )
                yield {"terminal": True, "reason": "timeout"}
                break

            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=_SSE_HEARTBEAT_SECONDS,
            )
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if not raw:
                continue
            parsed = _parse_message(raw)
            if parsed is None:
                continue
            yield parsed
            if _is_terminal_payload(parsed):
                break
    finally:
        await pubsub.unsubscribe(_channel(run_id))
        await pubsub.close()
