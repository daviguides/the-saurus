"""Shared test fixtures and helpers for pipeline tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from agno.agent import RunCompletedEvent


def mock_streaming_arun(fake_output: Any) -> MagicMock:
    """Create a mock for agent.arun that simulates streaming mode.

    Returns a MagicMock whose side_effect is an async generator
    yielding a single RunCompletedEvent with the fake output's content.
    This matches the streaming interface used by run_agent_with_retry.

    Uses MagicMock (not AsyncMock) because AsyncMock wraps the return
    in a coroutine, which breaks ``async for`` iteration over the generator.
    """

    async def _stream(*args: Any, **kwargs: Any):
        event = RunCompletedEvent(content=fake_output.content)
        yield event

    return MagicMock(side_effect=_stream)
