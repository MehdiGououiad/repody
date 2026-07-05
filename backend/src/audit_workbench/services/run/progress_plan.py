from __future__ import annotations

from typing import Any, Literal

from audit_workbench.extraction.document_model_branding import normalize_public_catalog_id
from audit_workbench.extraction.document_modes import (
    document_needs_extraction,
    parse_read_path,
    resolve_run_validation_mode,
)
from audit_workbench.extraction.extraction_display import plan_extraction_detail

StepStatus = Literal["pending", "active", "done"]

__all__ = [
    "StepStatus",
    "_queue_wait_detail",
    "_read_path_for_doc",
    "_step",
    "build_run_progress_plan",
    "mark_step_done",
    "progress_snapshot",
]


def _value(item: Any, key: str, default: Any = None) -> Any:
    value = getattr(item, key, None)
    if value is not None:
        return value
    if isinstance(item, dict):
        return item.get(key, default)
    return default


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
    document_model_id: str | None = None,
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
    if document_model_id:
        row["documentModelId"] = normalize_public_catalog_id(document_model_id)
    if duration_ms is not None:
        row["durationMs"] = duration_ms
    if gpu_cold_start_hint:
        row["gpuColdStartHint"] = True
    return row


def _queue_wait_detail() -> str:
    from audit_workbench.extraction.gpu_cold_start import is_serverless_vllm

    if is_serverless_vllm():
        return (
            "Waiting for a worker slot. Serverless GPU extraction can take 1-2 minutes "
            "on the first request after the GPU has been idle."
        )
    return (
        "Waiting for a worker slot - if another document is processing, "
        "this can take several minutes on CPU"
    )


def _read_path_for_doc(doc: Any, *, has_file: bool) -> tuple[str, str, str | None]:
    if not has_file:
        return "schema", "schema", None
    ext_mode = _value(doc, "extraction_mode", "document_model")
    path = parse_read_path(ext_mode)
    ocr = _value(doc, "document_model_id")
    return "document_model", path.id, ocr


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
    run_validation_mode = resolve_run_validation_mode(rules)
    for doc in workflow_docs:
        doc_id = _value(doc, "id", "")
        has_file = doc_id in docs_with_files
        if not document_needs_extraction(doc, has_file=has_file):
            continue
        doc_type = _value(doc, "document_type", "Document")
        mode, read_path, document_model_id = _read_path_for_doc(doc, has_file=has_file)
        steps.append(
            _step(
                f"extract-{doc_id}",
                f"Extract \u00b7 {doc_type}",
                mode=mode,
                read_path=read_path,
                validation_mode=run_validation_mode,
                document_model_id=document_model_id,
                detail=plan_extraction_detail(
                    doc, has_file=has_file, run_validation_mode=run_validation_mode
                ),
            )
        )
    for rule in rules:
        kind = (rule.get("kind") or "logic").lower()
        if kind == "llm":
            rule_id = rule.get("id") or "rule"
            name = rule.get("name") or "Rule"
            steps.append(
                _step(
                    f"rule-{rule_id}",
                    f"Validate \u00b7 {name}",
                    kind=kind,
                    detail="LLM rule evaluation",
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
                    f"Validate \u00b7 {name}",
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
                    f"Validate \u00b7 {name}",
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
    for index, step in enumerate(steps):
        if index < current_index:
            status: StepStatus = "done"
        elif index == current_index:
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
    cache_hit: bool = False,
) -> None:
    for step in steps:
        if step.get("id") == step_id:
            if duration_ms is not None:
                step["durationMs"] = duration_ms
            if detail:
                step["detail"] = detail
            if cache_hit:
                step["cacheHit"] = True
            return
