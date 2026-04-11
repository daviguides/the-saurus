"""Tests for the event bridge callback factory."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.agents.event_bridge import create_agent_event_callback
from pipeline.core import EventEmitter, EventType
from pipeline.core.persistence import create_job_dir


@pytest.fixture
def jobs_dir(tmp_path: Path) -> Path:
    return tmp_path / "jobs"


@pytest.fixture
def emitter(jobs_dir: Path) -> EventEmitter:
    create_job_dir("j1", jobs_dir)
    (jobs_dir / "j1" / "events.ndjson").touch()
    return EventEmitter("j1", jobs_dir)


def _make_event(cls_name: str, **kwargs: Any) -> Any:
    """Create a minimal mock Agno event by class name."""
    from unittest.mock import MagicMock

    # Import actual classes for isinstance checks
    from agno.agent import (
        RunCompletedEvent,
        RunContentEvent,
        RunErrorEvent,
        RunStartedEvent,
        ToolCallCompletedEvent,
        ToolCallStartedEvent,
    )

    cls_map = {
        "RunStartedEvent": RunStartedEvent,
        "RunContentEvent": RunContentEvent,
        "RunCompletedEvent": RunCompletedEvent,
        "RunErrorEvent": RunErrorEvent,
        "ToolCallStartedEvent": ToolCallStartedEvent,
        "ToolCallCompletedEvent": ToolCallCompletedEvent,
    }
    cls = cls_map[cls_name]

    # Create real instance with required fields
    event = cls.__new__(cls)
    # Set base fields
    event.created_at = int(time.time())
    event.event = cls_name
    event.agent_id = "agent-1"
    event.agent_name = "TestAgent"
    event.run_id = None
    event.parent_run_id = None
    event.session_id = None
    event.workflow_id = None
    event.workflow_run_id = None
    event.step_id = None
    event.step_name = None
    event.step_index = None
    event.tools = None
    event.content = None

    # Set class-specific defaults
    if cls_name in ("ToolCallStartedEvent", "ToolCallCompletedEvent"):
        event.tool = None
    if cls_name == "ToolCallCompletedEvent":
        event.images = None
        event.videos = None
        event.audio = None
    if cls_name == "RunContentEvent":
        event.content_type = "text"
        event.workflow_agent = False
        event.reasoning_content = None
        event.model_provider_data = None
        event.citations = None
        event.response_audio = None
        event.image = None
        event.references = None
        event.additional_input = None
        event.reasoning_steps = None
        event.reasoning_messages = None
    if cls_name == "RunCompletedEvent":
        event.content_type = "text"
        event.reasoning_content = None
        event.citations = None
        event.model_provider_data = None
        event.images = None
        event.videos = None
        event.audio = None
        event.response_audio = None
        event.references = None
        event.additional_input = None
        event.reasoning_steps = None
        event.reasoning_messages = None
        event.metadata = None
        event.metrics = None
        event.session_state = None
    if cls_name == "RunErrorEvent":
        event.error_type = None
        event.error_id = None
        event.additional_data = None
    if cls_name == "RunStartedEvent":
        event.model = "gpt-4o"
        event.model_provider = "openai"

    # Apply overrides
    for k, v in kwargs.items():
        setattr(event, k, v)

    return event


def _make_tool(**kwargs: Any) -> Any:
    """Create a mock ToolExecution."""
    from unittest.mock import MagicMock

    tool = MagicMock()
    tool.tool_name = kwargs.get("tool_name", "test_tool")
    tool.tool_args = kwargs.get("tool_args", {"key": "value"})
    tool.result = kwargs.get("result", "some result")
    tool.metrics = None
    return tool


class TestCreateAgentEventCallback:
    async def test_run_started_emits_agent_started(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage", paper_id="p1")
        event = _make_event("RunStartedEvent")

        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(event)

        emitter.emit.assert_called_once()
        call_args = emitter.emit.call_args
        assert call_args[0][0] == EventType.AGENT_STARTED
        payload = call_args[0][1]
        assert payload["agent_name"] == "TestAgent"
        assert payload["stage"] == "test_stage"
        assert payload["paper_id"] == "p1"
        assert payload["model"] == "gpt-4o"

    async def test_tool_call_started_emits_agent_tool_call(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")
        tool = _make_tool(tool_name="search_docs", tool_args={"query": "test"})
        event = _make_event("ToolCallStartedEvent", tool=tool)

        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(event)

        emitter.emit.assert_called_once()
        call_args = emitter.emit.call_args
        assert call_args[0][0] == EventType.AGENT_TOOL_CALL
        payload = call_args[0][1]
        assert payload["tool_name"] == "search_docs"
        assert "tool_args_preview" in payload

    async def test_tool_call_completed_emits_agent_tool_result(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")

        # Send ToolCallStarted first to set tool_t0
        tool_start = _make_tool(tool_name="search_docs")
        event_start = _make_event("ToolCallStartedEvent", tool=tool_start)
        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(event_start)

        # Now send ToolCallCompleted
        tool_end = _make_tool(tool_name="search_docs", result="found 3 results")
        event_end = _make_event("ToolCallCompletedEvent", tool=tool_end)
        await cb(event_end)

        assert emitter.emit.call_count == 2
        call_args = emitter.emit.call_args  # last call
        assert call_args[0][0] == EventType.AGENT_TOOL_RESULT
        payload = call_args[0][1]
        assert payload["tool_name"] == "search_docs"
        assert "elapsed_ms" in payload
        assert payload["result_len"] > 0

    async def test_run_content_emits_agent_content(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")
        event = _make_event("RunContentEvent", content="Hello world", content_type="text")

        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(event)

        emitter.emit.assert_called_once()
        call_args = emitter.emit.call_args
        assert call_args[0][0] == EventType.AGENT_CONTENT
        payload = call_args[0][1]
        assert payload["content_len"] == 11
        assert payload["content_type"] == "text"

    async def test_run_completed_emits_agent_completed_with_elapsed(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage", paper_id="p1")

        # First emit RunStarted to set t0
        start_event = _make_event("RunStartedEvent")
        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(start_event)

        # Then emit RunCompleted
        end_event = _make_event("RunCompletedEvent", content="result")
        await cb(end_event)

        assert emitter.emit.call_count == 2
        call_args = emitter.emit.call_args
        assert call_args[0][0] == EventType.AGENT_COMPLETED
        payload = call_args[0][1]
        assert payload["agent_name"] == "TestAgent"
        assert payload["paper_id"] == "p1"
        assert "elapsed_ms" in payload
        assert payload["elapsed_ms"] >= 0

    async def test_run_error_emits_agent_error(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")
        event = _make_event(
            "RunErrorEvent", content="Rate limit exceeded", error_type="RateLimitError"
        )

        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(event)

        emitter.emit.assert_called_once()
        call_args = emitter.emit.call_args
        assert call_args[0][0] == EventType.AGENT_ERROR
        payload = call_args[0][1]
        assert payload["error"] == "Rate limit exceeded"
        assert payload["error_type"] == "RateLimitError"

    async def test_unknown_event_is_ignored(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")
        emitter.emit = AsyncMock(wraps=emitter.emit)

        # Pass some random object
        await cb({"type": "unknown"})

        emitter.emit.assert_not_called()

    async def test_no_paper_id_omits_from_payload(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")
        event = _make_event("RunStartedEvent")

        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(event)

        payload = emitter.emit.call_args[0][1]
        assert "paper_id" not in payload

    async def test_tool_call_with_no_tool_is_ignored(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")
        event = _make_event("ToolCallStartedEvent", tool=None)

        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(event)

        emitter.emit.assert_not_called()

    async def test_run_content_with_none_content_is_ignored(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")
        event = _make_event("RunContentEvent", content=None)

        emitter.emit = AsyncMock(wraps=emitter.emit)
        await cb(event)

        emitter.emit.assert_not_called()

    async def test_emit_failure_does_not_propagate(self, emitter: EventEmitter):
        cb = create_agent_event_callback(emitter, "TestAgent", "test_stage")
        event = _make_event("RunStartedEvent")

        emitter.emit = AsyncMock(side_effect=RuntimeError("emit failed"))

        # Should not raise
        await cb(event)
