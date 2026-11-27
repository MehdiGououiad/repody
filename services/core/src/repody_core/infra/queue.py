"""Hatchet durable event publisher for ``repody_core``."""

from functools import cache

import structlog
from hatchet_sdk import Hatchet

from repody_common.contracts import FourEyesApprovalEvent
from repody_core.settings import get_settings

log = structlog.get_logger(__name__)

PIPELINE_WORKFLOW = "pipeline-execute"
APPROVAL_DECIDED_EVENT = "approval:decided"


@cache
def hatchet() -> Hatchet:
    """Return the cached Hatchet client (reads ``HATCHET_CLIENT_*`` on first use)."""
    return Hatchet()


class HatchetEventPublisher:
    """Publish Four-Eyes decisions to resume paused durable Hatchet tasks."""

    async def publish_approval_decision(self, event: FourEyesApprovalEvent) -> None:
        if not get_settings().hatchet_enabled:
            return
        await hatchet().event.aio_push(
            event_key=APPROVAL_DECIDED_EVENT,
            payload=event.model_dump(mode="json"),
            scope=event.approval_id,
        )
        log.info(
            "hatchet_approval_event_pushed",
            approval_id=event.approval_id,
            decision=event.decision,
        )
