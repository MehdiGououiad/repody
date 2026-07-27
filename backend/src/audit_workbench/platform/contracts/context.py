"""Prior agent outcomes bag — optional helper when constructing agent inputs.

ADR 007 handoff uses ``run_metadata.agentOutcomes`` + outbox ``agent_stage``, not this type.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from audit_workbench.platform.contracts.agent import AgentId, AgentOutcome


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Typed view over prior ``AgentOutcome`` values for a run."""

    run_id: str
    outcomes: tuple[AgentOutcome, ...] = ()

    def payload(self, agent: AgentId) -> Any | None:
        for outcome in reversed(self.outcomes):
            if outcome.agent is agent:
                return outcome.payload
        return None

    def outcome_for(self, agent: AgentId) -> AgentOutcome | None:
        for outcome in reversed(self.outcomes):
            if outcome.agent is agent:
                return outcome
        return None

    def with_outcome(self, outcome: AgentOutcome) -> AgentContext:
        return replace(self, outcomes=(*self.outcomes, outcome))
