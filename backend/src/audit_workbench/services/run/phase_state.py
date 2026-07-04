"""Run phase state for combined extract+validate pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from audit_workbench.db.models import Run, Workflow
from audit_workbench.extraction.base import ExtractionResult
from audit_workbench.services.run.snapshot import resolve_run_documents, resolve_run_rules
from audit_workbench.services.run_progress import build_run_progress_plan, mark_step_done


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
    docs_with_files = {rd.document_id for rd in run.documents if rd.document_id and rd.storage_key}
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
    mark_step_done(state.progress_steps, "queue", detail="Taskiq worker picked up job")
    return state
