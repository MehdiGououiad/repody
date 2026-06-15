"""Versioned Run progress domain events and UI mapper."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import Field

from audit_workbench.schemas.common import CamelModel

PROGRESS_EVENT_VERSION = 1


class RunProgressEventType(str, Enum):
    queue_waiting = "queue_waiting"
    extraction_started = "extraction_started"
    extraction_completed = "extraction_completed"
    rule_evaluated = "rule_evaluated"
    finalize_started = "finalize_started"
    run_failed = "run_failed"


class RunProgressEvent(CamelModel):
    version: int = PROGRESS_EVENT_VERSION
    type: RunProgressEventType
    run_id: str = Field(serialization_alias="runId")
    step_id: str = Field(serialization_alias="stepId")
    label: str = ""
    detail: str | None = None
    status: Literal["pending", "active", "done"] = "pending"
    read_path: str | None = Field(default=None, serialization_alias="readPath")
    validation_mode: str | None = Field(default=None, serialization_alias="validationMode")
    ocr_model: str | None = Field(default=None, serialization_alias="ocrModel")
    duration_ms: int | None = Field(default=None, serialization_alias="durationMs")
    gpu_cold_start_hint: bool = Field(default=False, serialization_alias="gpuColdStartHint")
    failed: bool = False


def progress_dict_from_event(event: RunProgressEvent, *, steps: list[dict[str, Any]], current_index: int) -> dict[str, Any]:
    """Apply a domain event onto the step list and return UI progress payload."""
    out_steps = [dict(step) for step in steps]
    for step in out_steps:
        if step.get("id") == event.step_id:
            step["status"] = event.status
            if event.detail:
                step["detail"] = event.detail
            if event.read_path:
                step["readPath"] = event.read_path
            if event.validation_mode:
                step["validationMode"] = event.validation_mode
            if event.ocr_model:
                step["ocrModel"] = event.ocr_model
            if event.duration_ms is not None:
                step["durationMs"] = event.duration_ms
            if event.gpu_cold_start_hint:
                step["gpuColdStartHint"] = True
            break

    payload: dict[str, Any] = {
        "currentIndex": current_index,
        "steps": out_steps,
        "label": event.label,
        "eventVersion": event.version,
        "lastEvent": event.type.value,
    }
    if event.failed:
        payload["failed"] = True
    return payload


def event_from_step_update(
    *,
    run_id: str,
    step_id: str,
    label: str,
    status: Literal["pending", "active", "done"],
    event_type: RunProgressEventType,
    detail: str | None = None,
    **extra: Any,
) -> RunProgressEvent:
    return RunProgressEvent(
        type=event_type,
        run_id=run_id,
        step_id=step_id,
        label=label,
        status=status,
        detail=detail,
        read_path=extra.get("read_path"),
        validation_mode=extra.get("validation_mode"),
        ocr_model=extra.get("ocr_model"),
        duration_ms=extra.get("duration_ms"),
        gpu_cold_start_hint=extra.get("gpu_cold_start_hint", False),
        failed=extra.get("failed", False),
    )
