"""Bridge between Agno streaming events and the pipeline EventEmitter.

Creates async callbacks that map Agno agent lifecycle events
(RunStarted, ToolCallStarted, etc.) to pipeline EventType entries
and emit them through the EventEmitter for NDJSON + WebSocket delivery.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from agno.agent import (
    RunCompletedEvent,
    RunContentEvent,
    RunErrorEvent,
    RunStartedEvent,
    ToolCallCompletedEvent,
    ToolCallStartedEvent,
)

from pipeline.agents.step_messages import get_step_message, get_technical_message, is_internal_tool
from pipeline.core.events import EventEmitter, EventType

logger = logging.getLogger(__name__)

PREVIEW_MAX = 200


def _truncate(text: str, max_len: int = PREVIEW_MAX) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def create_agent_event_callback(
    emitter: EventEmitter,
    agent_name: str,
    stage: str,
    paper_id: str | None = None,
    context: dict[str, Any] | None = None,
) -> Callable[[Any], Awaitable[None]]:
    """Build an on_event callback that forwards Agno events to the pipeline emitter.

    Args:
        emitter: Pipeline EventEmitter for the current job.
        agent_name: Name of the agent (e.g. "PaperAnalyzer").
        stage: Pipeline stage (e.g. "paper_analysis").
        paper_id: Optional paper ID for per-paper stages.
        context: Optional dict with runtime values for message interpolation
                 (e.g. paper_title, theme_count).
    """
    state: dict[str, Any] = {}
    ctx = context or {}

    def _base_payload() -> dict[str, Any]:
        payload: dict[str, Any] = {"agent_name": agent_name, "stage": stage}
        if paper_id is not None:
            payload["paper_id"] = paper_id
        return payload

    def _enrich(payload: dict[str, Any], event_type: str) -> None:
        """Add human-readable and technical messages to payload."""
        payload["message"] = get_step_message(event_type, agent_name, ctx)
        payload["technical_message"] = get_technical_message(
            event_type, agent_name, payload,
        )

    async def on_event(event: Any) -> None:
        try:
            if isinstance(event, RunStartedEvent):
                state["t0"] = time.monotonic()
                payload = _base_payload()
                payload["model"] = getattr(event, "model", "")
                _enrich(payload, "agent_started")
                await emitter.emit(EventType.AGENT_STARTED, payload)

            elif isinstance(event, ToolCallStartedEvent):
                tool = getattr(event, "tool", None)
                if tool is None:
                    return
                tool_name = getattr(tool, "tool_name", "") or ""
                if is_internal_tool(tool_name):
                    return
                state["tool_t0"] = time.monotonic()
                payload = _base_payload()
                payload["tool_name"] = tool_name
                raw_args = getattr(tool, "tool_args", None)
                if raw_args:
                    payload["tool_args_preview"] = _truncate(str(raw_args))
                _enrich(payload, "agent_tool_call")
                await emitter.emit(EventType.AGENT_TOOL_CALL, payload)

            elif isinstance(event, ToolCallCompletedEvent):
                tool = getattr(event, "tool", None)
                if tool is None:
                    return
                tool_name = getattr(tool, "tool_name", "") or ""
                if is_internal_tool(tool_name):
                    state.pop("tool_t0", None)
                    return
                payload = _base_payload()
                payload["tool_name"] = tool_name
                result = getattr(tool, "result", None)
                payload["result_len"] = len(str(result)) if result else 0
                tool_t0 = state.pop("tool_t0", None)
                if tool_t0 is not None:
                    payload["elapsed_ms"] = int((time.monotonic() - tool_t0) * 1000)
                _enrich(payload, "agent_tool_result")
                await emitter.emit(EventType.AGENT_TOOL_RESULT, payload)

            elif isinstance(event, RunContentEvent):
                content = getattr(event, "content", None)
                if content is None:
                    return
                payload = _base_payload()
                payload["content_len"] = len(str(content))
                payload["content_type"] = getattr(event, "content_type", "text")
                _enrich(payload, "agent_content")
                await emitter.emit(EventType.AGENT_CONTENT, payload)

            elif isinstance(event, RunCompletedEvent):
                payload = _base_payload()
                t0 = state.get("t0")
                if t0 is not None:
                    payload["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
                _enrich(payload, "agent_completed")
                await emitter.emit(EventType.AGENT_COMPLETED, payload)

            elif isinstance(event, RunErrorEvent):
                payload = _base_payload()
                payload["error"] = _truncate(
                    getattr(event, "content", "") or str(event)
                )
                payload["error_type"] = getattr(event, "error_type", None) or ""
                t0 = state.get("t0")
                if t0 is not None:
                    payload["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
                _enrich(payload, "agent_error")
                await emitter.emit(EventType.AGENT_ERROR, payload)

        except Exception:
            logger.warning(
                "[%s] event_bridge emit failed for %s",
                agent_name,
                type(event).__name__,
                exc_info=True,
            )

    return on_event
