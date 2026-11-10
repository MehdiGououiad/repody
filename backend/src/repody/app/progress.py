"""Run progress: a step plan stored on the run, which clients poll (``GET /v1/runs/{id}``).

Queue position is not stored: it is counted when a client reads a queued run.
"""

import asyncio
from typing import Any

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra import db
from repody.infra.models import Run
from repody.schemas.run import ProgressStep, RunProgress
from repody.schemas.workflow import WorkflowDefinition

QUEUE_STEP = "queue"
RULES_STEP = "rules"
FINALIZE_STEP = "finalize"


def extract_step(document_id: str) -> str:
    return f"extract-{document_id}"


def plan(definition: WorkflowDefinition, document_ids_with_files: set[str]) -> RunProgress:
    """Queued -> extract each document -> check the rules -> save the report."""
    steps = [ProgressStep(id=QUEUE_STEP, kind="queue", status="active")]
    steps += [
        ProgressStep(id=extract_step(doc.id), kind="extract", document_type=doc.document_type)
        for doc in definition.documents
        if doc.id in document_ids_with_files and doc.wants_extraction
    ]
    if definition.rules:
        steps.append(ProgressStep(id=RULES_STEP, kind="rules", rule_count=len(definition.rules)))
    steps.append(ProgressStep(id=FINALIZE_STEP, kind="finalize"))
    return RunProgress(steps=steps)


async def with_queue_position(session: AsyncSession, run: Run) -> RunProgress | None:
    if run.progress is None:
        return None
    progress = RunProgress.model_validate(run.progress)
    if run.status == "queued":
        # Queue order is (created_at, id); a row comparison counts the runs ahead in the same
        # query as the depth.
        ahead_of_run = tuple_(Run.created_at, Run.id) < tuple_(run.created_at, run.id)
        ahead, depth = (
            await session.execute(
                select(func.count().filter(ahead_of_run), func.count()).where(
                    Run.status == "queued"
                )
            )
        ).one()
        progress.queue_position, progress.queue_depth = ahead + 1, depth
    return progress


class Tracker:
    """The worker's view of a run's progress; every change is saved on the run.

    Steps can run concurrently (documents are extracted in parallel), so each one is started
    and finished by id, and saves are serialized.
    """

    def __init__(self, run_id: str, progress: RunProgress) -> None:
        self.run_id = run_id
        self.progress = progress
        self._lock = asyncio.Lock()

    def _step(self, step_id: str) -> ProgressStep | None:
        return next((s for s in self.progress.steps if s.id == step_id), None)

    async def start(self, step_id: str) -> None:
        """Mark ``step_id`` active; the queue step is done once any other step starts."""
        if queue := self._step(QUEUE_STEP):
            queue.status = "done"
        if step := self._step(step_id):
            step.status = "active"
        await self._save()

    async def finish(self, step_id: str, **values: Any) -> None:
        """Mark ``step_id`` done, setting ``values`` (duration, cache hit, …) on it."""
        if step := self._step(step_id):
            for name, value in values.items():
                setattr(step, name, value)
            step.status = "done"
        await self._save()

    def complete(self) -> dict[str, Any]:
        """Every step done: the final progress, saved by the caller with the report."""
        for step in self.progress.steps:
            step.status = "done"
        return self.progress.model_dump()

    async def _save(self) -> None:
        async with self._lock:
            data = self.progress.model_dump()
            async with db.session_factory() as session:
                await session.execute(
                    update(Run).where(Run.id == self.run_id).values(progress=data)
                )
                await session.commit()
