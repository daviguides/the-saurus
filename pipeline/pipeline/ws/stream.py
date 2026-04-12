"""WebSocket endpoint for live event streaming and emitter registry."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

from pipeline.core import Event, EventEmitter

logger = logging.getLogger(__name__)

# B3: Heartbeat interval for WebSocket receive loop (seconds)
WS_HEARTBEAT_TIMEOUT = 60.0

_emitters: dict[str, EventEmitter] = {}


def register_emitter(job_id: str, emitter: EventEmitter) -> None:
    _emitters[job_id] = emitter


def remove_emitter(job_id: str) -> None:
    """Remove emitter for a finished job to prevent memory leaks."""
    _emitters.pop(job_id, None)


def clear_all_emitters() -> None:
    """Remove all emitters (e.g., on shutdown). R5: Prevent memory leaks."""
    _emitters.clear()


def get_or_create_emitter(job_id: str, jobs_dir: Path) -> EventEmitter:
    if job_id not in _emitters:
        _emitters[job_id] = EventEmitter(job_id, jobs_dir)
    return _emitters[job_id]


async def websocket_stream(websocket: WebSocket, job_id: str, jobs_dir: Path) -> None:
    """Handle a WebSocket connection for live event streaming."""
    job_path = jobs_dir / job_id
    if not job_path.is_dir():
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()

    emitter = get_or_create_emitter(job_id, jobs_dir)

    async def on_event(event: Event) -> None:
        try:
            await websocket.send_json(event.model_dump(mode="json"))
        except Exception:
            logger.debug("WS send failed for job %s", job_id, exc_info=True)

    emitter.add_listener(on_event)
    try:
        while True:
            try:
                await asyncio.wait_for(
                    websocket.receive_text(), timeout=WS_HEARTBEAT_TIMEOUT
                )
            except TimeoutError:
                # B3: Send ping to detect dead connections
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        emitter.remove_listener(on_event)
