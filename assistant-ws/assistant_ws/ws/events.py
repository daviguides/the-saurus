import socketio

from assistant_ws.ws.chat_service import ChatService
from assistant_ws.ws.session import SessionManager
from assistant_ws.ws.connection import ConnectionManager

session_mgr = SessionManager()
conn_mgr = ConnectionManager()
chat_service = ChatService()


def register_events(sio: socketio.AsyncServer):

    @sio.event
    async def connect(sid, environ, auth=None):
        session_id = None
        if auth and isinstance(auth, dict):
            session_id = auth.get("session_id")

        if not session_id:
            session_id = session_mgr.create_session()
        else:
            session_mgr.ensure_session(session_id)

        conn_mgr.register(sid, session_id)
        await sio.emit("session_created", {"session_id": session_id}, to=sid)

    @sio.event
    async def disconnect(sid):
        conn_mgr.unregister(sid)

    @sio.event
    async def message(sid, data):
        session_id = conn_mgr.get_session(sid)
        if not session_id:
            await sio.emit("error", {"message": "No session found"}, to=sid)
            return

        text = data.get("text", "") if isinstance(data, dict) else str(data)
        if not text.strip():
            return

        await chat_service.process_message(sio, sid, session_id, text)
