"""Run phase state for combined extract+validate pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from audit_workbench.db.models import Run
from audit_workbench.extraction.base import ExtractionResult
from audit_workbench.extraction.processing_paths import validation_mode_label
from audit_workbench.services.run.helpers import rules_payload
from audit_workbench.services.run.snapshot import resolve_run_documents, resolve_run_rules
from audit_workbench.services.run_progress import build_run_progress_plan, mark_step_done


PHASE_EXTRACTED = "extracted"


def decode_precomputed_llm(raw: Any) -> dict[str, tuple[str, str]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, tuple[str, str]] = {}
    for rule_id, pair in raw.items():
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            out[str(rule_id)] = (str(pair[0]), str(pair[1]))
    return out


@dataclass
class ExtractionPhaseResult:
    """Typed metadata persisted between Hatchet extract and validate tasks."""

    precomputed_llm: dict[str, tuple[str, str]] = field(default_factory=dict)
    extraction_ms: int = 0
    fields_extracted: int = 0
    step_index: int = 0
    validation_mode: str = "logic_only"
    multi_document: bool = False

    @classmethod
    def from_state(cls, state: RunPhaseState) -> ExtractionPhaseResult:
        return cls(
            precomputed_llm=dict(state.precomputed_llm),
            extraction_ms=state.extraction_total_ms,
            fields_extracted=state.fields_extracted,
            step_index=state.step_index,
            validation_mode=state.validation_mode,
            multi_document=state.multi_document,
        )

    def to_metadata(self) -> dict:
        return {
            "phase": PHASE_EXTRACTED,
            "precomputedLlm": {k: list(v) for k, v in self.precomputed_llm.items()},
            "extractionMs": self.extraction_ms,
            "fieldsExtracted": self.fields_extracted,
            "multiDocument": self.multi_document,
            "validationMode": self.validation_mode,
            "validationLabel": validation_mode_label(self.validation_mode),
            "stepIndex": self.step_index,
        }

    @classmethod
    def from_metadata(cls, meta: dict) -> ExtractionPhaseResult | None:
        if meta.get("phase") != PHASE_EXTRACTED:
            return None
        return cls(
            precomputed_llm=decode_precomputed_llm(meta.get("precomputedLlm")),
            extraction_ms=int(meta.get("extractionMs") or 0),
            fields_extracted=int(meta.get("fieldsExtracted") or 0),
            step_index=int(meta.get("stepIndex") or 0),
            validation_mode=str(meta.get("validationMode") or "logic_only"),
            multi_document=bool(meta.get("multiDocument")),
        )

    def apply_to(self, state: RunPhaseState) -> None:
        state.precomputed_llm = dict(self.precomputed_llm)
        state.extraction_total_ms = self.extraction_ms
        state.fields_extracted = self.fields_extracted
        state.step_index = self.step_index
        state.validation_mode = self.validation_mode
        state.multi_document = self.multi_document


@dataclass
class RunPhaseState:
    run_id: str
    run: Run
    workflow: Workflow
    workflow_docs: list
    rules_payload: list[dict]
    progress_steps: list[dict]
    docs_with_files: set[str]
    multi_document: bool
    step_index: int = 0
    extraction_results: list[tuple[str, ExtractionResult]] = field(default_factory=list)
    fields_extracted: int = 0
    extraction_total_ms: int = 0
    validation_mode: str = "logic_only"
    precomputed_llm: dict[str, tuple[str, str]] = field(default_factory=dict)


def _base_phase_state(run: Run) -> RunPhaseState:
    workflow = run.workflow
    workflow_docs = resolve_run_documents(run)
    payload = resolve_run_rules(run, workflow)
    docs_with_files = {
        rd.document_id for rd in run.documents if rd.document_id and rd.storage_key
    }
    docs_with_schema = sum(
        1 for doc in workflow_docs if any(f.name.strip() for f in doc.schema_fields)
    )
    progress_steps = build_run_progress_plan(
        workflow_docs=workflow_docs,
        rules=payload,
        docs_with_files=docs_with_files,
    )
    return RunPhaseState(
        run_id=run.id,
        run=run,
        workflow=workflow,
        workflow_docs=workflow_docs,
        rules_payload=payload,
        progress_steps=progress_steps,
        docs_with_files=docs_with_files,
        multi_document=docs_with_schema > 1,
    )


def build_phase_state(run: Run) -> RunPhaseState:
    """Fresh state after claim — marks the queue step as picked up."""
    state = _base_phase_state(run)
    mark_step_done(state.progress_steps, "queue", detail="Hatchet worker picked up job")
    return state
