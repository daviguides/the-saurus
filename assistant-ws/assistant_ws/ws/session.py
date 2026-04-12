import time
import uuid
from dataclasses import dataclass, field

from assistant_ws.config import settings


@dataclass
class Session:
    session_id: str
    messages: list[dict] = field(default_factory=list)
    last_accessed: float = field(default_factory=time.monotonic)

    def touch(self):
        self.last_accessed = time.monotonic()


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._ttl_seconds: float = settings.session_ttl_minutes * 60

    def create_session(self) -> str:
        self._evict_expired()
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = Session(session_id=session_id)
        return session_id

    def ensure_session(self, session_id: str) -> Session:
        self._evict_expired()
        session = self._sessions.get(session_id)
        if session is None:
            session = Session(session_id=session_id)
            self._sessions[session_id] = session
        session.touch()
        return session

    def get_session(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if self._is_expired(session):
            self._sessions.pop(session_id, None)
            return None
        session.touch()
        return session

    def add_message(self, session_id: str, role: str, content: str):
        session = self._sessions.get(session_id)
        if session:
            session.touch()
            session.messages.append({"role": role, "content": content})

    def remove_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def _is_expired(self, session: Session) -> bool:
        return (time.monotonic() - session.last_accessed) > self._ttl_seconds

    def _evict_expired(self):
        now = time.monotonic()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if (now - s.last_accessed) > self._ttl_seconds
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
