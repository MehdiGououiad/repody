"""Live run progress: a step plan stored on the run and pushed over Redis pub/sub (SSE).

Queue position is not stored: it is counted when a client reads a queued run.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra import db
from repody.infra.models import Run
from repody.infra.redis import get_redis
from repody.schemas.run import ProgressStep, RunProgress
from repody.schemas.workflow import WorkflowDefinition

STREAM_SECONDS = 3600
RULES_STEP = "rules"
FINALIZE_STEP = "finalize"


def _channel(run_id: str) -> str:
    return f"run-events:{run_id}"


def extract_step(document_id: str) -> str:
    return f"extract-{document_id}"


def plan(definition: WorkflowDefinition, document_ids_with_files: set[str]) -> RunProgress:
    """Queued -> extract each document -> check the rules -> save the report."""
    steps = [ProgressStep(id="queue", label="Queued for a worker", status="active")]
    steps += [
        ProgressStep(id=extract_step(doc.id), label=f"Extract · {doc.document_type or 'Document'}")
        for doc in definition.documents
        if doc.id in document_ids_with_files and doc.wants_extraction
    ]
    if definition.rules:
        steps.append(ProgressStep(id=RULES_STEP, label=f"Check {len(definition.rules)} rule(s)"))
    steps.append(ProgressStep(id=FINALIZE_STEP, label="Save the audit report"))
    return RunProgress(label="Waiting for a worker…", steps=steps)


async def publish(run_id: str, message: dict[str, Any]) -> None:
    await get_redis().publish(_channel(run_id), json.dumps(message))


async def subscribe(run_id: str) -> AsyncIterator[str]:
    """JSON messages for one run until it finishes (or the stream times out)."""
    async with get_redis().pubsub() as pubsub:
        await pubsub.subscribe(_channel(run_id))
        deadline = time.monotonic() + STREAM_SECONDS
        while time.monotonic() < deadline:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
            if message is None:
                continue
            yield message["data"]
            if json.loads(message["data"]).get("terminal"):
                return


async def with_queue_position(session: AsyncSession, run: Run) -> RunProgress | None:
    if run.progress is None:
        return None
    progress = RunProgress.model_validate(run.progress)
    if run.status == "queued":
        queued = Run.status == "queued"
        ahead = await session.scalar(
            select(func.count()).where(
                queued,
                or_(
                    Run.created_at < run.created_at,
                    and_(Run.created_at == run.created_at, Run.id < run.id),
                ),
            )
        )
        depth = await session.scalar(select(func.count()).where(queued))
        progress.queue_position, progress.queue_depth = (ahead or 0) + 1, depth or 0
    return progress


class Tracker:
    """The worker's view of a run's progress: each change is stored on the run and published."""

    def __init__(self, run_id: str, progress: RunProgress) -> None:
        self.run_id = run_id
        self.progress = progress

    def step(self, step_id: str) -> ProgressStep | None:
        return next((s for s in self.progress.steps if s.id == step_id), None)

    async def start(self, step_id: str, label: str) -> None:
        """Mark every step before ``step_id`` done and ``step_id`` active."""
        ids = [s.id for s in self.progress.steps]
        index = ids.index(step_id) if step_id in ids else -1
        for i, step in enumerate(self.progress.steps):
            if i < index:
                step.status = "done"
            elif i == index:
                step.status = "active"
        self.progress.label = label
        data = self.progress.model_dump()
        async with db.session_factory() as session:
            await session.execute(update(Run).where(Run.id == self.run_id).values(progress=data))
            await session.commit()
        await publish(self.run_id, {"progress": data})

    def finish(self) -> dict[str, Any]:
        for step in self.progress.steps:
            step.status = "done"
        self.progress.label = "Complete"
        return self.progress.model_dump()
