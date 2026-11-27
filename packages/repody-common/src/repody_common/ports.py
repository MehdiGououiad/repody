"""Swappable protocol ports so engines, models, and sinks can be replaced cleanly."""

from typing import Any, Literal, Protocol

from repody_common.contracts import ArtifactRef, FraudFinding
from repody_common.entitlements import EntitlementState


class FraudDetector(Protocol):
    """Pluggable forensic detector (Tier 1 PDF/crypto, Tier 2 logic, Tier 3 visual)."""

    name: str
    tier: Literal[1, 2, 3]

    async def analyze(
        self,
        artifact: ArtifactRef,
        data: bytes,
        context: dict[str, Any],
    ) -> list[FraudFinding]: ...


class VisualExplainer(Protocol):
    """Optional VLM adapter for cropped high-severity hotspot explanations."""

    async def explain_region(
        self,
        image_png: bytes,
        findings: list[FraudFinding],
    ) -> str | None: ...


class EntitlementProvider(Protocol):
    """Source of verified module entitlements for API and UI gating."""

    def current(self) -> EntitlementState: ...


class AuditSink(Protocol):
    """Append-only regulatory audit event sink."""

    async def record(
        self,
        *,
        actor_sub: str,
        account_id: str | None,
        module: str,
        action: str,
        resource_id: str,
        detail: dict[str, Any],
    ) -> str: ...
