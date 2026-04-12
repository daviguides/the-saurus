import asyncio
import logging
import time

import socketio
from agno.run.agent import RunEvent
from agno.run.team import TeamRunEvent
from agno.team import Team

from assistant_ws.agents.coordinator.team import build_coordinator_team
from assistant_ws.config import settings
from assistant_ws.ws.schemas import DoneEvent, StepEvent, TokenEvent

logger = logging.getLogger(__name__)

# Team cache: one Team instance per session to preserve InMemoryDb history
_team_cache: dict[str, Team] = {}
_team_cache_timestamps: dict[str, float] = {}
_team_build_lock = asyncio.Lock()

# Per-session concurrency guard: only one LLM request at a time per session
_session_locks: dict[str, asyncio.Lock] = {}


async def get_or_create_team(session_id: str) -> Team:
    async with _team_build_lock:
        if session_id in _team_cache:
            _team_cache_timestamps[session_id] = time.monotonic()
            return _team_cache[session_id]

    # Build outside the lock to avoid blocking other sessions
    team = await build_coordinator_team()

    async with _team_build_lock:
        # Double-check: another coroutine may have built it while we waited
        if session_id not in _team_cache:
            _team_cache[session_id] = team
            _team_cache_timestamps[session_id] = time.monotonic()
        return _team_cache[session_id]


def evict_team(session_id: str) -> None:
    _team_cache.pop(session_id, None)
    _team_cache_timestamps.pop(session_id, None)
    _session_locks.pop(session_id, None)


def evict_expired_teams() -> None:
    """Remove teams that have exceeded the session TTL."""
    ttl_seconds = settings.session_ttl_minutes * 60
    now = time.monotonic()
    expired = [
        sid
        for sid, ts in _team_cache_timestamps.items()
        if (now - ts) > ttl_seconds
    ]
    for sid in expired:
        evict_team(sid)


def _get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


# Human-friendly labels for MCP tool names
_TOOL_LABELS: dict[str, str] = {
    "get_paper_themes": "Looking up paper themes",
    "get_claims_by_theme": "Fetching claims by theme",
    "get_theme_map": "Loading theme map",
    "get_theme_review": "Reading theme review",
    "get_literature_review": "Loading literature review",
    "search_claims": "Searching claims",
}


class ChatService:
    async def process_message(
        self, sio: socketio.AsyncServer, sid: str, session_id: str, text: str
    ):
        lock = _get_session_lock(session_id)
        if lock.locked():
            try:
                await sio.emit(
                    "error",
                    {"message": "A request is already in progress. Please wait."},
                    to=sid,
                    namespace="/chat",
                )
            except Exception:
                logger.warning("Failed to emit busy error to %s", sid)
            return

        async with lock:
            start = time.monotonic()

            try:
                team = await get_or_create_team(session_id)
                full_response = ""

                async for event in asyncio.wait_for(
                    _consume_stream(team, text, session_id),
                    timeout=settings.team_run_timeout_seconds,
                ):
                    ev = event.event

                    # Team-level content delta -> stream token to client
                    if ev == TeamRunEvent.run_content.value and event.content:
                        chunk = str(event.content)
                        full_response += chunk
                        token_evt = TokenEvent(content=chunk)
                        await sio.emit("token", token_evt.model_dump(), to=sid, namespace="/chat")

                    # Agent tool call started -> emit step with tool name
                    elif ev == RunEvent.tool_call_started.value and event.tool:
                        tool_name = event.tool.tool_name or "tool"
                        label = _TOOL_LABELS.get(tool_name, f"Using {tool_name}")
                        step_evt = StepEvent(step=f"{label}...", tool=tool_name)
                        await sio.emit("step", step_evt.model_dump(exclude_none=True), to=sid, namespace="/chat")

                    # Team run error
                    elif ev == TeamRunEvent.run_error.value:
                        logger.error(
                            "Team run error for session %s: %s",
                            session_id,
                            event.content,
                        )
                        await sio.emit(
                            "error",
                            {"message": "An error occurred while processing your request."},
                            to=sid,
                            namespace="/chat",
                        )
                        return

                elapsed_ms = int((time.monotonic() - start) * 1000)
                done_evt = DoneEvent(metrics={"elapsed_time_ms": elapsed_ms})
                await sio.emit("done", done_evt.model_dump(), to=sid, namespace="/chat")

            except asyncio.TimeoutError:
                logger.error("Team run timed out for session %s", session_id)
                try:
                    await sio.emit(
                        "error",
                        {"message": "Request timed out. Please try again."},
                        to=sid,
                        namespace="/chat",
                    )
                except Exception:
                    logger.warning("Failed to emit timeout error to %s", sid)

            except Exception:
                logger.exception("Error processing message for session %s", session_id)
                try:
                    await sio.emit(
                        "error",
                        {"message": "An internal error occurred. Please try again."},
                        to=sid,
                        namespace="/chat",
                    )
                except Exception:
                    logger.warning("Failed to emit error to %s", sid)


async def _consume_stream(team: Team, text: str, session_id: str):
    """Async generator wrapper so we can pass team.arun to wait_for."""
    async for event in team.arun(text, session_id=session_id, stream=True):
        yield event
