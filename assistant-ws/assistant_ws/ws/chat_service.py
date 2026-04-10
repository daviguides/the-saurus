import time

import socketio

from assistant_ws.agents.coordinator.team import build_coordinator_team
from assistant_ws.ws.session import SessionManager

session_mgr = SessionManager()


class ChatService:
    async def process_message(
        self, sio: socketio.AsyncServer, sid: str, session_id: str, text: str
    ):
        start = time.monotonic()
        session_mgr.add_message(session_id, "user", text)

        try:
            team = await build_coordinator_team()
            full_response = ""

            await sio.emit("step", {"step": "Analyzing your question..."}, to=sid)

            async for event in team.arun(text, stream=True):
                if hasattr(event, "content") and event.content:
                    chunk = event.content
                    full_response += chunk
                    await sio.emit("token", {"content": chunk}, to=sid)

            session_mgr.add_message(session_id, "assistant", full_response)

            elapsed_ms = int((time.monotonic() - start) * 1000)
            await sio.emit(
                "done",
                {"metrics": {"elapsed_time_ms": elapsed_ms}},
                to=sid,
            )
        except Exception as e:
            await sio.emit("error", {"message": str(e)}, to=sid)
