"""Run enqueue domain errors — mapped to HTTP in the API layer."""

from __future__ import annotations


class RunEnqueueError(Exception):
    """Base class for run enqueue failures."""


class WorkflowNotFoundError(RunEnqueueError):
    pass


class UnauthorizedRunError(RunEnqueueError):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ForbiddenRunError(RunEnqueueError):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class WorkflowNotDeployedError(RunEnqueueError):
    pass
