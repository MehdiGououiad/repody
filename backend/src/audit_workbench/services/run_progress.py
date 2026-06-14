from __future__ import annotations

import time
from typing import Any, Literal

from audit_workbench.db.models import Run
from audit_workbench.extraction.processing_paths import (
    parse_read_path,
    parse_validation_mode,
    validation_mode_label,
)
from audit_workbench.extraction.document_model_branding import (
    normalize_public_catalog_id,
    public_document_model_label,
)
from audit_workbench.settings import get_settings

StepStatus = Literal["pending", "active", "done"]

_last_progress_commit: dict[str, float] = {}
_MAX_PROGRESS_CACHE = 512


def _value(item: Any, key: str, default: Any = None) -> Any:
    """Read ORM/snapshot attributes and dictionary values uniformly."""
    value = getattr(item, key, None)
    if value is not None:
        return value
    if isinstance(item, dict):
        return item.get(key, default)
    return default


def clear_progress_commit_cache(run_id: str | None = None) -> None:
    if run_id:
        _last_progress_commit.pop(run_id, None)
    else:
        _last_progress_commit.clear()


def _touch_progress_cache(run_id: str, now: float) -> None:
    if run_id in _last_progress_commit:
        _last_progress_commit.pop(run_id)
    _last_progress_commit[run_id] = now
    while len(_last_progress_commit) > _MAX_PROGRESS_CACHE:
        _last_progress_commit.pop(next(iter(_last_progress_commit)))


def _step(
    step_id: str,
    label: str,
    *,
    status: StepStatus = "pending",
    mode: str | None = None,
    kind: str | None = None,
    detail: str | None = None,
    read_path: str | None = None,
    validation_mode: str | None = None,
    ocr_model: str | None = None,
    duration_ms: int | None = None,
    gpu_cold_start_hint: bool = False,
) -> dict[str, Any]:
    row: dict[str, Any] = {"id": step_id, "label": label, "status": status}
    if mode:
        row["mode"] = mode
    if kind:
        row["kind"] = kind
    if detail:
        row["detail"] = detail
    if read_path:
        row["readPath"] = read_path
    if validation_mode:
        row["validationMode"] = validation_mode
    if ocr_model:
        row["ocrModel"] = normalize_public_catalog_id(ocr_model)
    if duration_ms is not None:
        row["durationMs"] = duration_ms
    if gpu_cold_start_hint:
        row["gpuColdStartHint"] = True
    return row


def _queue_wait_detail() -> str:
    from audit_workbench.extraction.gpu_cold_start import is_serverless_vllm

    if is_serverless_vllm():
        return (
            "Waiting for a worker slot. Serverless GPU extraction can take 1–2 minutes "
            "on the first request after the GPU has been idle."
        )
    return (
        "Waiting for a worker slot — if another document is processing, "
        "this can take several minutes on CPU"
    )


def _read_path_for_doc(doc: Any, *, has_file: bool) -> tuple[str, str, str | None]:
    if not has_file:
        return "schema", "schema", None
    ext_mode = _value(doc, "extraction_mode", "document_model")
    path = parse_read_path(ext_mode)
    ocr = _value(doc, "ocr_model")
    return "document_model", path.id, ocr


def _extract_detail(doc: Any, *, has_file: bool) -> str:
    if not has_file:
        return "Schema placeholders (no file uploaded)"
    extraction_mode = _value(doc, "extraction_mode", "auto")
    read_spec = parse_read_path(extraction_mode)
    val = parse_validation_mode(
        _value(doc, "validation_mode"),
        extraction_mode=extraction_mode,
    )
    ocr = _value(doc, "ocr_model")
    parts = [f"Read: {read_spec.label}", f"Validation: {validation_mode_label(val)}"]
    if ocr and read_spec.show_ocr_model:
        parts.append(f"Model: {public_document_model_label(ocr)}")
    return " · ".join(parts)


def build_run_progress_plan(
    *,
    workflow_docs: list[Any],
    rules: list[dict],
    docs_with_files: set[str],
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        _step(
            "queue",
            "Queued for worker",
            detail=_queue_wait_detail(),
        ),
    ]
    for doc in workflow_docs:
        schema_fields = _value(doc, "schema_fields", [])
        has_schema = any(
            str(_value(f, "name", "")).strip()
            for f in schema_fields
        )
        if not has_schema:
            continue
        doc_id = _value(doc, "id", "")
        doc_type = _value(doc, "document_type", "Document")
        has_file = doc_id in docs_with_files
        mode, read_path, ocr_model = _read_path_for_doc(doc, has_file=has_file)
        extraction_mode = _value(doc, "extraction_mode", "auto")
        val_mode = parse_validation_mode(
            _value(doc, "validation_mode"),
            extraction_mode=extraction_mode,
        )
        steps.append(
            _step(
                f"extract-{doc_id}",
                f"Extract · {doc_type}",
                mode=mode,
                read_path=read_path,
                validation_mode=val_mode,
                ocr_model=ocr_model,
                detail=_extract_detail(doc, has_file=has_file),
            )
        )
    for rule in rules:
        kind = (rule.get("kind") or "logic").lower()
        if kind == "llm":
            rule_id = rule.get("id") or "rule"
            name = rule.get("name") or "Rule"
            detail = "LLM rule evaluation"
            steps.append(
                _step(
                    f"rule-{rule_id}",
                    f"Validate · {name}",
                    kind=kind,
                    detail=detail,
                )
            )
            continue
        from audit_workbench.rules.conditions import logic_check_entries

        checks = logic_check_entries(rule)
        if not checks:
            rule_id = rule.get("id") or "rule"
            name = rule.get("name") or "Rule"
            steps.append(
                _step(
                    f"rule-{rule_id}",
                    f"Validate · {name}",
                    kind="logic",
                    detail="Logic expression on extracted fields",
                )
            )
            continue
        for check in checks:
            check_id = check.get("id") or "rule"
            name = check.get("name") or "Check"
            expr = (check.get("body") or "").strip()
            steps.append(
                _step(
                    f"rule-{check_id}",
                    f"Validate · {name}",
                    kind="logic",
                    detail=f"Expression: {expr}" if expr else "Logic check on extracted fields",
                )
            )
    steps.append(_step("finalize", "Build audit report", detail="Persist fields and rule results"))
    return steps


def progress_snapshot(
    steps: list[dict[str, Any]],
    current_index: int,
    label: str,
) -> dict[str, Any]:
    out_steps: list[dict[str, Any]] = []
    for i, step in enumerate(steps):
        if i < current_index:
            status: StepStatus = "done"
        elif i == current_index:
            status = "active"
        else:
            status = "pending"
        out_steps.append({**step, "status": status})
    return {
        "currentIndex": current_index,
        "steps": out_steps,
        "label": label,
    }


def mark_step_done(
    steps: list[dict[str, Any]],
    step_id: str,
    *,
    duration_ms: int | None = None,
    detail: str | None = None,
) -> None:
    for step in steps:
        if step.get("id") == step_id:
            if duration_ms is not None:
                step["durationMs"] = duration_ms
            if detail:
                step["detail"] = detail
            return


async def set_run_progress(
    session: object,
    run_id: str,
    steps: list[dict[str, Any]],
    current_index: int,
    label: str,
    *,
    force: bool = False,
) -> None:
    """Publish live progress over SSE; persist to DB on an interval (or when forced)."""
    from sqlalchemy.ext.asyncio import AsyncSession

    progress = progress_snapshot(steps, current_index, label)

    from audit_workbench.services.run_events import publish_run_progress

    await publish_run_progress(run_id, progress)

    settings = get_settings()
    interval_s = settings.progress_commit_interval_ms / 1000.0
    now = time.monotonic()
    last = _last_progress_commit.get(run_id, 0.0)
    if not force and (now - last) < interval_s:
        return

    if isinstance(session, AsyncSession):
        run = await session.get(Run, run_id)
        if run:
            run.progress = progress
        _touch_progress_cache(run_id, now)
        return

    from audit_workbench.db.base import async_session_factory

    async with async_session_factory() as progress_session:
        run = await progress_session.get(Run, run_id)
        if not run:
            return
        run.progress = progress
        await progress_session.commit()
    _touch_progress_cache(run_id, now)


async def init_queued_progress(session: object, run_id: str) -> None:
    steps = [
        _step(
            "queue",
            "Queued for worker",
            detail=(
                "Waiting for an OCR worker slot — if another document is processing, "
                "this can take several minutes on CPU"
            ),
        )
    ]
    await set_run_progress(session, run_id, steps, 0, "Waiting for worker…", force=True)


async def fail_run_progress(run_id: str, error: str) -> None:
    """Publish a terminal failed progress snapshot (queue step failed)."""
    detail = error[:500]
    steps = [
        _step(
            "queue",
            "Run failed",
            status="done",
            detail=detail,
        )
    ]
    progress = {
        "currentIndex": 0,
        "steps": steps,
        "label": detail,
        "failed": True,
    }

    from audit_workbench.services.run_events import publish_run_progress

    await publish_run_progress(run_id, progress)

    from audit_workbench.services.run_events import publish_run_terminal

    await publish_run_terminal(run_id, status="failed")

    from audit_workbench.db.base import async_session_factory

    async with async_session_factory() as session:
        run = await session.get(Run, run_id)
        if run:
            run.progress = progress
            await session.commit()
    clear_progress_commit_cache(run_id)
