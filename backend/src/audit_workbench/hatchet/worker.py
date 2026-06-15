from __future__ import annotations

import asyncio
import os

import structlog

from audit_workbench.hatchet.client import get_hatchet
from audit_workbench.hatchet.workflows.audit_run import get_audit_run_workflow
from audit_workbench.observability.bootstrap import init_observability
from audit_workbench.settings import get_settings

log = structlog.get_logger()


async def _warmup_ocr_models(pool: str) -> None:
    from audit_workbench.extraction.repody_vlm import warmup_repody_vlm

    settings = get_settings()
    if pool == "ocr" and settings.repody_vlm_warmup_on_start:
        await warmup_repody_vlm()


async def _startup_warmup(pool: str) -> None:
    try:
        if pool == "ocr":
            await _warmup_ocr_models(pool)
    finally:
        # Warmup uses asyncio.run() in a temporary loop; close pooled httpx
        # clients so Hatchet's loop does not inherit stale connections.
        from audit_workbench.inference.http_pool import close_async_http_client

        await close_async_http_client()


def main() -> None:
    init_observability()
    pool = os.getenv("AUDIT_WORKER_POOL", "ocr")
    slots = int(
        os.getenv(
            "AUDIT_WORKER_SLOTS",
            os.getenv(
                "AUDIT_WORKER_OCR_MAX_JOBS" if pool == "ocr" else "AUDIT_WORKER_FAST_MAX_JOBS",
                "1" if pool == "ocr" else "4",
            ),
        )
    )
    name = f"repody-worker-{pool}"
    log.info("hatchet_worker_starting", name=name, pool=pool, slots=slots)

    asyncio.run(_startup_warmup(pool))

    hatchet = get_hatchet()
    worker = hatchet.worker(
        name,
        labels={"pool": pool},
        slots=slots,
        workflows=[get_audit_run_workflow()],
    )
    worker.start()


if __name__ == "__main__":
    main()
