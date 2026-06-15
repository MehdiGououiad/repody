"""Simulate Hatchet dispatch in unit tests (worker logic, no Hatchet server)."""

from __future__ import annotations


async def process_run_as_worker(run_id: str) -> None:
    import audit_workbench.db.base as db_base
    from audit_workbench.services.run_processor import process_run

    async with db_base.async_session_factory() as session:
        try:
            await process_run(session, run_id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispatch_audit_run_simulated(run_id: str, **_kwargs: object) -> str:
    await process_run_as_worker(run_id)
    return run_id
