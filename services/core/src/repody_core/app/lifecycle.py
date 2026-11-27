"""Explicit state-machine transition tables for ``repody_core``."""

from repody_core.schemas.approvals import ApprovalStatus
from repody_core.schemas.cases import CaseStatus, PipelineStatus

CASE_TRANSITIONS: dict[CaseStatus, tuple[CaseStatus, ...]] = {
    "open": ("in_progress", "waiting_maker", "failed"),
    "in_progress": ("waiting_maker", "waiting_checker", "approved", "rejected", "failed"),
    "waiting_maker": ("waiting_checker", "rejected", "failed"),
    "waiting_checker": ("approved", "rejected", "waiting_maker", "failed"),
    "approved": (),
    "rejected": (),
    "failed": (),
}

APPROVAL_TRANSITIONS: dict[ApprovalStatus, tuple[ApprovalStatus, ...]] = {
    "waiting_maker": ("waiting_checker", "rejected"),
    "returned_to_maker": ("waiting_checker", "rejected"),
    "waiting_checker": ("approved", "rejected", "returned_to_maker"),
    "approved": (),
    "rejected": (),
}

PIPELINE_TRANSITIONS: dict[PipelineStatus, tuple[PipelineStatus, ...]] = {
    "queued": ("running", "failed"),
    "running": ("waiting_approval", "done", "rejected", "failed"),
    "waiting_approval": ("running", "done", "rejected", "failed"),
    "done": (),
    "rejected": (),
    "failed": (),
}


def assert_case_transition(current: CaseStatus, target: CaseStatus) -> None:
    """Raise ``ValueError`` if transitioning a case from ``current`` to ``target`` is invalid."""
    if target not in CASE_TRANSITIONS[current]:
        raise ValueError(f"Invalid case transition: {current} -> {target}.")


def assert_approval_transition(current: ApprovalStatus, target: ApprovalStatus) -> None:
    """Raise ``ValueError`` if transitioning an approval from ``current`` to ``target`` is invalid."""
    if target not in APPROVAL_TRANSITIONS[current]:
        raise ValueError(f"Invalid approval transition: {current} -> {target}.")


def assert_pipeline_transition(current: PipelineStatus, target: PipelineStatus) -> None:
    """Raise ``ValueError`` if transitioning a pipeline from ``current`` to ``target`` is invalid."""
    if target not in PIPELINE_TRANSITIONS[current]:
        raise ValueError(f"Invalid pipeline transition: {current} -> {target}.")
