"""IDP progress / UI presentation — kept out of extract/validate ports.

State is a plain record; every operation is a module-level function that takes
it explicitly, so there is no hidden receiver and each step can be called or
tested on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from repody.agents.idp.compose import ExtractionJob
from repody.agents.idp.contracts import IdpExtractionMeta
from repody.app.run.helpers import extract_label, progress_mode
from repody.app.run.progress import (
    mark_step_done,
    set_run_progress,
    step_index_for,
)
from repody.app.run.snapshot import SnapshotDocument
from repody.extraction.modes import (
    DEFAULT_READ_PATH_ID,
    ValidationMode,
    completed_extraction_detail,
    is_serverless_inference,
    parse_read_path,
    read_path_label,
    validation_mode_label,
)
from repody.rules.types import rule_kind

_GPU_COLD_START_DETAIL = "Serverless GPU may need 1-2 min to start on the first request after idle"


@dataclass
class IdpProgress:
    """Mutable progress for one run: the step plan, which step is live, and timing."""

    run_id: str
    steps: list[dict]
    files: set[str]
    snap_by_id: dict[str, SnapshotDocument]
    validation_mode: ValidationMode
    step_index: int = 1
    validation_started_at: float | None = None


def activate_step(progress: IdpProgress, step_id: str) -> int:
    """Point the run at `step_id`, leaving the index untouched if it is unknown."""
    found = step_index_for(progress.steps, step_id)
    if found is not None:
        progress.step_index = found
    return progress.step_index


def first_rule_step_id(progress: IdpProgress) -> str | None:
    for step in progress.steps:
        step_id = str(step.get("id") or "")
        if step_id.startswith("rule-"):
            return step_id
    return None


def _annotate_gpu_cold_start(progress: IdpProgress, step_id: str) -> None:
    for step in progress.steps:
        if step.get("id") == step_id:
            step["gpuColdStartHint"] = True
            return


async def report_extract_start(
    progress: IdpProgress, job: ExtractionJob, index: int, total: int
) -> None:
    has_file = job.document_id in progress.files
    mode = progress_mode(has_file=has_file)
    step_id = f"extract-{job.document_id}"
    activate_step(progress, step_id)

    detail = read_path_label(parse_read_path(job.spec.extraction_mode or DEFAULT_READ_PATH_ID).id)
    if is_serverless_inference() and mode == "document_model":
        detail = f"{detail} · {_GPU_COLD_START_DETAIL}"
        _annotate_gpu_cold_start(progress, step_id)

    await set_run_progress(
        None,
        progress.run_id,
        progress.steps,
        progress.step_index,
        extract_label(job.spec.label, mode=mode, detail=detail),
        # Push the first and last document eagerly; the rest ride the throttle.
        force=(index == 0 or index == total - 1),
    )


async def report_extract_done(
    progress: IdpProgress, job: ExtractionJob, meta: IdpExtractionMeta
) -> None:
    step_id = f"extract-{job.document_id}"
    mark_step_done(
        progress.steps,
        step_id,
        duration_ms=meta.extraction_ms,
        detail=completed_extraction_detail(meta),
        cache_hit=meta.cache_hit,
    )
    activate_step(progress, step_id)
    await set_run_progress(
        None,
        progress.run_id,
        progress.steps,
        progress.step_index,
        extract_label(job.spec.label, mode="document_model"),
        force=True,
    )


async def report_rule_start(progress: IdpProgress, rule: dict) -> None:
    name = rule.get("name") or "Rule"
    step_id = f"rule-{rule.get('id') or 'rule'}"
    kind = rule_kind(rule)
    for step in progress.steps:
        if step.get("id") == step_id:
            step["detail"] = (
                "Evaluating LLM rule against extracted fields"
                if kind == "llm"
                else "Logic expression on extracted fields"
            )
            break
    activate_step(progress, step_id)
    await set_run_progress(
        None,
        progress.run_id,
        progress.steps,
        progress.step_index,
        f"LLM rule · {name}…" if kind == "llm" else f"Validate · {name}…",
        force=True,
    )


async def report_validation_start(progress: IdpProgress, *, has_rules: bool) -> None:
    if not has_rules:
        return
    progress.validation_started_at = datetime.now(UTC).timestamp()
    first_rule = first_rule_step_id(progress)
    if first_rule:
        activate_step(progress, first_rule)
    await set_run_progress(
        None,
        progress.run_id,
        progress.steps,
        progress.step_index,
        f"Validating rules ({validation_mode_label(progress.validation_mode)})…",
        force=True,
    )


def validation_elapsed_ms(progress: IdpProgress) -> int:
    """Milliseconds since validation began, or 0 when there were no rules to run."""
    if progress.validation_started_at is None:
        return 0
    return int((datetime.now(UTC).timestamp() - progress.validation_started_at) * 1000)


def mark_rules_done(progress: IdpProgress, rule_results) -> None:
    for row in rule_results:
        mark_step_done(
            progress.steps,
            f"rule-{row.rule_id}",
            detail=f"Status: {row.status} — {row.detail or 'OK'}",
        )


async def report_saving(progress: IdpProgress) -> None:
    activate_step(progress, "finalize")
    await set_run_progress(
        None,
        progress.run_id,
        progress.steps,
        progress.step_index,
        "Saving audit report…",
        force=True,
    )
