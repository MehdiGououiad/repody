"""Computer-use agent (SKIPPED scaffold until implemented)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from repody.agents.computer_use.contracts import ComputerUseInput, ComputerUseOutcome

if TYPE_CHECKING:
    from repody.agents.computer_use.run import (
        execute_computer_use as execute_computer_use,
    )

__all__ = ["ComputerUseInput", "ComputerUseOutcome", "execute_computer_use"]


def __getattr__(name: str) -> Any:
    if name == "execute_computer_use":
        from repody.agents.computer_use.run import execute_computer_use

        return execute_computer_use
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
