"""Agent protocol for pipeline stages."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Agent(Protocol):
    """Structural interface for pipeline agents.

    Each pipeline stage delegates to an Agent implementation.
    Agents receive stage-specific input and return structured output.
    """

    async def run(self, data: dict[str, Any], *, on_event: Any = None) -> dict[str, Any]: ...
