import logging
import time

import socketio
from agno.run.agent import RunEvent
from agno.run.team import TeamRunEvent
from agno.team import Team

from assistant_ws.agents.coordinator.team import build_coordinator_team

logger = logging.getLogger(__name__)

# Team cache: one Team instance per session to preserve InMemoryDb history
_team_cache: dict[str, Team] = {}


async def get_or_create_team(session_id: str) -> Team:
    if session_id not in _team_cache:
        _team_cache[session_id] = await build_coordinator_team()
    return _team_cache[session_id]


def evict_team(session_id: str) -> None:
    _team_cache.pop(session_id, None)


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
        start = time.monotonic()

        try:
            team = await get_or_create_team(session_id)
            full_response = ""

            async for event in team.arun(text, session_id=session_id, stream=True):
                ev = event.event

                # Team-level content delta → stream token to client
                if ev == TeamRunEvent.run_content.value and event.content:
                    chunk = str(event.content)
                    full_response += chunk
                    await sio.emit("token", {"content": chunk}, to=sid)

                # Agent tool call started → emit step with tool name
                elif ev == RunEvent.tool_call_started.value and event.tool:
                    tool_name = event.tool.tool_name or "tool"
                    label = _TOOL_LABELS.get(tool_name, f"Using {tool_name}")
                    await sio.emit(
                        "step",
                        {"step": f"{label}...", "tool": tool_name},
                        to=sid,
                    )

                # Team run error
                elif ev == TeamRunEvent.run_error.value:
                    error_msg = str(event.content) if event.content else "Unknown error"
                    await sio.emit("error", {"message": error_msg}, to=sid)
                    return

            elapsed_ms = int((time.monotonic() - start) * 1000)
            await sio.emit(
                "done",
                {"metrics": {"elapsed_time_ms": elapsed_ms}},
                to=sid,
            )
        except Exception as e:
            logger.exception("Error processing message for session %s", session_id)
            await sio.emit("error", {"message": str(e)}, to=sid)
