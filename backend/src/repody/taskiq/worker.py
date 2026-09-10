"""Taskiq worker entrypoint — one pool per process (extract|fast).

Prefer invoking via the official CLI when possible::

    taskiq worker repody.taskiq.worker:broker --max-async-tasks=N --log-level=INFO

``main()`` uses Taskiq's ``WorkerArgs`` + ``run_worker`` API so we never mutate ``sys.argv``.
"""

from __future__ import annotations

import signal

import structlog
from taskiq import TaskiqEvents
from taskiq.cli.common_args import LogLevel
from taskiq.cli.worker.args import WorkerArgs
from taskiq.cli.worker.run import run_worker

from repody.extraction.warmup import warmup_repody_vlm
from repody.inference.openai_compat import close_openai_clients
from repody.infra.http import close_http_clients
from repody.infra.observability.bootstrap import init_observability
from repody.settings import get_settings
from repody.taskiq.broker import get_broker
from repody.taskiq.tasks import get_process_audit_run_task

log = structlog.get_logger()

settings = get_settings()
pool = settings.worker_pool
broker = get_broker(pool)
_process_audit_run_task = get_process_audit_run_task(pool)


async def _warmup_document_models(worker_pool: str) -> None:
    if worker_pool != "extract":
        return

    vlm_status = await warmup_repody_vlm() if settings.repody_vlm_warmup_on_start else "disabled"
    log.info(
        "extract_pool_warmup_done",
        repody_vlm=vlm_status,
    )


async def _startup_warmup(worker_pool: str) -> None:
    try:
        if worker_pool == "extract":
            await _warmup_document_models(worker_pool)
    finally:
        await close_openai_clients()
        await close_http_clients()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _on_worker_startup(_state: object) -> None:
    init_observability()
    await _startup_warmup(pool)


def _worker_slots() -> int:
    if pool == "extract":
        return settings.worker_extract_max_jobs
    return settings.worker_fast_max_jobs


def main() -> None:
    # Taskiq registers SIGQUIT; Windows has no SIGQUIT.
    if not hasattr(signal, "SIGQUIT"):
        signal.SIGQUIT = signal.SIGTERM  # type: ignore[attr-defined,misc]

    slots = _worker_slots()
    name = f"repody-worker-{pool}"
    log.info("taskiq_worker_starting", name=name, pool=pool, slots=slots)

    run_worker(
        WorkerArgs(
            broker="repody.taskiq.worker:broker",
            modules=[],
            max_async_tasks=slots,
            log_level=LogLevel.INFO,
        )
    )


if __name__ == "__main__":
    main()
