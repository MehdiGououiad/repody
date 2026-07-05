from __future__ import annotations


class InvalidRunTransition(Exception):
    """Raised when a Run lifecycle action violates aggregate invariants."""

    def __init__(self, run_id: str, from_status: str, action: str) -> None:
        self.run_id = run_id
        self.from_status = from_status
        self.action = action
        super().__init__(f"Run {run_id} cannot {action} from status {from_status!r}")
