"""Taskiq worker entrypoint — one pool per process (ocr or fast)."""

from __future__ import annotations

import signal
import sys

import structlog
from taskiq import TaskiqEvents

from audit_workbench.observability.bootstrap import init_observability
from audit_workbench.settings import get_settings
from audit_workbench.taskiq.broker import get_broker
from audit_workbench.taskiq.tasks import get_process_audit_run_task

log = structlog.get_logger()

settings = get_settings()
pool = settings.worker_pool
broker = get_broker(pool)
_process_audit_run_task = get_process_audit_run_task(pool)


async def _warmup_ocr_models(worker_pool: str) -> None:
    from audit_workbench.extraction.repody_vlm import warmup_repody_vlm

    if worker_pool != "ocr":
        return

    vlm_status = await warmup_repody_vlm() if settings.repody_vlm_warmup_on_start else "disabled"
    log.info(
        "ocr_worker_warmup_done",
        repody_vlm=vlm_status,
    )


async def _startup_warmup(worker_pool: str) -> None:
    try:
        if worker_pool == "ocr":
            await _warmup_ocr_models(worker_pool)
    finally:
        from audit_workbench.inference.openai_compat import close_openai_clients

        await close_openai_clients()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _on_worker_startup(_state: object) -> None:
    init_observability()
    await _startup_warmup(pool)


def _worker_slots() -> int:
    if pool == "ocr":
        return settings.worker_ocr_max_jobs
    return settings.worker_fast_max_jobs


def main() -> None:
    # Taskiq registers SIGQUIT; Windows has no SIGQUIT.
    if not hasattr(signal, "SIGQUIT"):
        signal.SIGQUIT = signal.SIGTERM  # type: ignore[attr-defined,misc]

    slots = _worker_slots()
    name = f"repody-worker-{pool}"
    log.info("taskiq_worker_starting", name=name, pool=pool, slots=slots)

    sys.argv = [
        "taskiq",
        "worker",
        "audit_workbench.taskiq.worker:broker",
        f"--max-async-tasks={slots}",
        "--log-level=INFO",
    ]
    from taskiq.__main__ import main as taskiq_main

    taskiq_main()


if __name__ == "__main__":
    main()
