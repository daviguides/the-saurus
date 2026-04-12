import logging
import uuid

import socketio

from assistant_ws.config import settings
from assistant_ws.ws.chat_service import ChatService, evict_team
from assistant_ws.ws.connection import ConnectionManager
from assistant_ws.ws.schemas import IncomingMessage
from assistant_ws.ws.session import SessionManager

logger = logging.getLogger(__name__)

session_mgr = SessionManager()
conn_mgr = ConnectionManager()
chat_service = ChatService()

_UUID4_LEN = 36


def _is_valid_uuid4(val: str) -> bool:
    try:
        uuid.UUID(val, version=4)
        return True
    except (ValueError, AttributeError):
        return False


def register_events(sio: socketio.AsyncServer):

    @sio.event(namespace="/chat")
    async def connect(sid, environ, auth=None):
        # Auth: validate shared-secret token if configured (opt-in: None = open)
        if settings.ws_auth_token is not None:
            token = None
            if auth and isinstance(auth, dict):
                token = auth.get("token")
            if token != settings.ws_auth_token:
                logger.warning("Rejected connection %s: invalid auth token", sid)
                raise socketio.exceptions.ConnectionRefusedError("Authentication failed")

        # Always generate server-side session ID (ignore client-supplied ones)
        session_id = session_mgr.create_session()

        conn_mgr.register(sid, session_id)
        await sio.emit("session_ready", {"session_id": session_id}, to=sid, namespace="/chat")

    @sio.event(namespace="/chat")
    async def disconnect(sid):
        session_id = conn_mgr.get_session(sid)
        if session_id:
            evict_team(session_id)
        conn_mgr.unregister(sid)

    @sio.event(namespace="/chat")
    async def message(sid, data):
        session_id = conn_mgr.get_session(sid)
        if not session_id:
            await sio.emit("error", {"message": "No session found"}, to=sid, namespace="/chat")
            return

        # Validate incoming message using schema
        try:
            if isinstance(data, dict):
                msg = IncomingMessage(**data)
            else:
                msg = IncomingMessage(text=str(data))
        except Exception:
            await sio.emit(
                "error", {"message": "Invalid message format"}, to=sid, namespace="/chat"
            )
            return

        text = msg.text.strip()
        if not text:
            await sio.emit(
                "error",
                {"message": "Message cannot be empty"},
                to=sid,
                namespace="/chat",
            )
            return

        if len(text) > settings.max_message_length:
            await sio.emit(
                "error",
                {"message": f"Message too long (max {settings.max_message_length} characters)"},
                to=sid,
                namespace="/chat",
            )
            return

        await chat_service.process_message(sio, sid, session_id, text)
