"""Async Socket.IO client for the assistant WebSocket service."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

import socketio

from assistant_test_client.schemas import (
    ChatResponse,
    DoneEvent,
    ErrorEvent,
    StepEvent,
    TokenEvent,
)

# Union of all events the client can yield
Event = TokenEvent | StepEvent | DoneEvent | ErrorEvent


class AssistantClient:
    """Thin async wrapper around the /chat Socket.IO namespace."""

    def __init__(self, url: str = "http://localhost:8001", timeout: float = 60.0):
        self._url = url
        self._timeout = timeout
        self._sio = socketio.AsyncClient(reconnection=False)
        self._session_id: str | None = None
        self._event_queue: asyncio.Queue[Event | None] = asyncio.Queue()

        # Register namespace handlers
        self._sio.on("session_ready", self._on_session_ready, namespace="/chat")
        self._sio.on("token", self._on_token, namespace="/chat")
        self._sio.on("step", self._on_step, namespace="/chat")
        self._sio.on("done", self._on_done, namespace="/chat")
        self._sio.on("error", self._on_error, namespace="/chat")

    # -- properties ----------------------------------------------------------

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def connected(self) -> bool:
        return self._sio.connected

    # -- connection ----------------------------------------------------------

    async def connect(self, session_id: str | None = None) -> str:
        """Connect to the assistant and return the server-assigned session_id."""
        self._session_id = None
        ready = asyncio.Event()

        original_handler = self._on_session_ready

        async def _capture_ready(data: dict[str, Any]):
            await original_handler(data)
            ready.set()

        self._sio.on("session_ready", _capture_ready, namespace="/chat")

        await self._sio.connect(self._url, namespaces=["/chat"], wait_timeout=self._timeout)

        try:
            await asyncio.wait_for(ready.wait(), timeout=self._timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Timed out waiting for session_ready event") from None
        finally:
            # Restore the original handler
            self._sio.on("session_ready", self._on_session_ready, namespace="/chat")

        assert self._session_id is not None
        return self._session_id

    async def disconnect(self) -> None:
        if self._sio.connected:
            await self._sio.disconnect()

    # -- messaging -----------------------------------------------------------

    async def send_message(self, text: str) -> AsyncGenerator[Event]:
        """Send a message and yield events until done or error."""
        # Drain any stale events
        while not self._event_queue.empty():
            self._event_queue.get_nowait()

        await self._sio.emit("message", {"text": text}, namespace="/chat")

        start = time.monotonic()
        while True:
            remaining = self._timeout - (time.monotonic() - start)
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for response")
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                raise TimeoutError("Timed out waiting for response") from None

            if event is None:
                return

            yield event

            if isinstance(event, (DoneEvent, ErrorEvent)):
                return

    async def send_and_collect(self, text: str) -> ChatResponse:
        """Send a message and collect the full response."""
        start = time.monotonic()
        response = ChatResponse()
        async for event in self.send_message(text):
            if isinstance(event, TokenEvent):
                response.content += event.content
            elif isinstance(event, StepEvent):
                response.steps.append(event)
            elif isinstance(event, DoneEvent):
                response.metrics = event.metrics
            elif isinstance(event, ErrorEvent):
                raise RuntimeError(f"Server error: {event.message}")
        response.elapsed_ms = (time.monotonic() - start) * 1000
        return response

    # -- Socket.IO callbacks -------------------------------------------------

    async def _on_session_ready(self, data: dict[str, Any]) -> None:
        self._session_id = data.get("session_id")

    async def _on_token(self, data: dict[str, Any]) -> None:
        await self._event_queue.put(TokenEvent(**data))

    async def _on_step(self, data: dict[str, Any]) -> None:
        await self._event_queue.put(StepEvent(**data))

    async def _on_done(self, data: dict[str, Any]) -> None:
        await self._event_queue.put(DoneEvent(**data))

    async def _on_error(self, data: dict[str, Any]) -> None:
        await self._event_queue.put(ErrorEvent(**data))
