"""Event schema, types, and emitter for the pipeline event system."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    PAPER_INGESTED = "paper_ingested"
    PAPER_PROCESSED = "paper_processed"
    PAPER_ANALYZED = "paper_analyzed"
    THEME_EXTRACTED = "theme_extracted"
    THEME_DEDUPLICATED = "theme_deduplicated"
    CLAIM_EXTRACTED = "claim_extracted"
    REVIEW_GENERATED = "review_generated"
    AGENT_STARTED = "agent_started"
    AGENT_TOOL_CALL = "agent_tool_call"
    AGENT_TOOL_RESULT = "agent_tool_result"
    AGENT_CONTENT = "agent_content"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"


class Event(BaseModel):
    """Single pipeline event, serialized as one NDJSON line."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    job_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


Listener = Callable[[Event], Awaitable[None]]


class EventEmitter:
    """Per-job event emitter: appends NDJSON and broadcasts to listeners."""

    def __init__(self, job_id: str, jobs_dir: Path) -> None:
        self.job_id = job_id
        self._ndjson_path = jobs_dir / job_id / "events.ndjson"
        self._listeners: list[Listener] = []

    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: Listener) -> None:
        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    async def emit(
        self, event_type: EventType | str, payload: dict[str, Any] | None = None
    ) -> Event:
        event = Event(
            event_type=str(event_type),
            job_id=self.job_id,
            payload=payload or {},
        )

        line = event.model_dump_json() + "\n"
        await asyncio.to_thread(self._append_line, line)

        if self._listeners:
            results = await asyncio.gather(
                *[cb(event) for cb in self._listeners],
                return_exceptions=True,
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        "Listener %d raised %s for event %s: %s",
                        i, type(result).__name__, event.event_type, result,
                    )

        return event

    def _append_line(self, line: str) -> None:
        # R6: Intentionally open-per-write to guarantee flush/fsync on each event.
        # Keeps NDJSON durable even if the process crashes mid-pipeline.
        with open(self._ndjson_path, "a") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
