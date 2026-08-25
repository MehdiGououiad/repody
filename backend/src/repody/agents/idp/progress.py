"""IDP progress / UI presentation — kept out of extract/validate ports."""

from __future__ import annotations

from dataclasses import dataclass, field
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
class IdpProgressPresenter:
    """Progress step labels, GPU cold-start hints, and run progress writes."""

    run_id: str
    progress_steps: list[dict]
    files: set[str]
    snap_by_id: dict[str, SnapshotDocument]
    validation_mode: ValidationMode
    step_index: int = 1
    _validation_started: float | None = field(default=None, repr=False)

    def activate(self, step_id: str) -> int:
        found = step_index_for(self.progress_steps, step_id)
        if found is not None:
            self.step_index = found
        return self.step_index

    def first_rule_step_id(self) -> str | None:
        for step in self.progress_steps:
            sid = str(step.get("id") or "")
            if sid.startswith("rule-"):
                return sid
        return None

    async def on_extract_start(self, job: ExtractionJob, index: int, total: int) -> None:
        has_file = job.document_id in self.files
        prog_mode = progress_mode(has_file=has_file)
        step_id = f"extract-{job.document_id}"
        self.activate(step_id)

        read_label = read_path_label(
            parse_read_path(job.spec.extraction_mode or DEFAULT_READ_PATH_ID).id
        )
        detail = read_label
        if is_serverless_inference() and prog_mode == "document_model":
            detail = f"{detail} · {_GPU_COLD_START_DETAIL}"
            for step in self.progress_steps:
                if step.get("id") == step_id:
                    step["gpuColdStartHint"] = True
                    break

        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            extract_label(job.spec.label, mode=prog_mode, detail=detail),
            force=(index == 0 or index == total - 1),
        )

    async def on_extract_done(self, job: ExtractionJob, meta: IdpExtractionMeta) -> None:
        step_id = f"extract-{job.document_id}"
        mark_step_done(
            self.progress_steps,
            step_id,
            duration_ms=meta.extraction_ms,
            detail=completed_extraction_detail(meta),
            cache_hit=meta.cache_hit,
        )
        self.activate(step_id)
        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            extract_label(job.spec.label, mode="document_model"),
            force=True,
        )

    async def on_rule_start(self, rule: dict) -> None:
        name = rule.get("name") or "Rule"
        rule_id = rule.get("id") or "rule"
        step_id = f"rule-{rule_id}"
        kind = rule_kind(rule)
        for step in self.progress_steps:
            if step.get("id") == step_id:
                step["detail"] = (
                    "Evaluating LLM rule against extracted fields"
                    if kind == "llm"
                    else "Logic expression on extracted fields"
                )
                break
        self.activate(step_id)
        label = f"LLM rule · {name}…" if kind == "llm" else f"Validate · {name}…"
        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            label,
            force=True,
        )

    async def on_validation_start(self, *, has_rules: bool) -> None:
        if not has_rules:
            return
        self._validation_started = datetime.now(UTC).timestamp()
        first_rule = self.first_rule_step_id()
        if first_rule:
            self.activate(first_rule)
        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            f"Validating rules ({validation_mode_label(self.validation_mode)})…",
            force=True,
        )

    def validation_elapsed_ms(self) -> int:
        if self._validation_started is None:
            return 0
        return int((datetime.now(UTC).timestamp() - self._validation_started) * 1000)

    def mark_rules_done(self, rule_results) -> None:
        for row in rule_results:
            mark_step_done(
                self.progress_steps,
                f"rule-{row.rule_id}",
                detail=f"Status: {row.status} — {row.detail or 'OK'}",
            )

    async def mark_saving(self) -> None:
        self.activate("finalize")
        await set_run_progress(
            None,
            self.run_id,
            self.progress_steps,
            self.step_index,
            "Saving audit report…",
            force=True,
        )
