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
) -> Callable[[Any], Awaitable[None]]:
    """Build an on_event callback that forwards Agno events to the pipeline emitter.

    Args:
        emitter: Pipeline EventEmitter for the current job.
        agent_name: Name of the agent (e.g. "PaperAnalyzer").
        stage: Pipeline stage (e.g. "paper_analysis").
        paper_id: Optional paper ID for per-paper stages.
    """
    state: dict[str, Any] = {}

    def _base_payload() -> dict[str, Any]:
        payload: dict[str, Any] = {"agent_name": agent_name, "stage": stage}
        if paper_id is not None:
            payload["paper_id"] = paper_id
        return payload

    async def on_event(event: Any) -> None:
        try:
            if isinstance(event, RunStartedEvent):
                state["t0"] = time.monotonic()
                payload = _base_payload()
                payload["model"] = getattr(event, "model", "")
                await emitter.emit(EventType.AGENT_STARTED, payload)

            elif isinstance(event, ToolCallStartedEvent):
                tool = getattr(event, "tool", None)
                if tool is None:
                    return
                state["tool_t0"] = time.monotonic()
                payload = _base_payload()
                payload["tool_name"] = getattr(tool, "tool_name", "") or ""
                raw_args = getattr(tool, "tool_args", None)
                if raw_args:
                    payload["tool_args_preview"] = _truncate(str(raw_args))
                await emitter.emit(EventType.AGENT_TOOL_CALL, payload)

            elif isinstance(event, ToolCallCompletedEvent):
                tool = getattr(event, "tool", None)
                if tool is None:
                    return
                payload = _base_payload()
                payload["tool_name"] = getattr(tool, "tool_name", "") or ""
                result = getattr(tool, "result", None)
                payload["result_len"] = len(str(result)) if result else 0
                tool_t0 = state.pop("tool_t0", None)
                if tool_t0 is not None:
                    payload["elapsed_ms"] = int((time.monotonic() - tool_t0) * 1000)
                await emitter.emit(EventType.AGENT_TOOL_RESULT, payload)

            elif isinstance(event, RunContentEvent):
                content = getattr(event, "content", None)
                if content is None:
                    return
                payload = _base_payload()
                payload["content_len"] = len(str(content))
                payload["content_type"] = getattr(event, "content_type", "text")
                await emitter.emit(EventType.AGENT_CONTENT, payload)

            elif isinstance(event, RunCompletedEvent):
                payload = _base_payload()
                t0 = state.get("t0")
                if t0 is not None:
                    payload["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
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
                await emitter.emit(EventType.AGENT_ERROR, payload)

        except Exception:
            logger.warning(
                "[%s] event_bridge emit failed for %s",
                agent_name,
                type(event).__name__,
                exc_info=True,
            )

    return on_event
