import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    session_id: str
    messages: list[dict] = field(default_factory=list)


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = Session(session_id=session_id)
        return session_id

    def ensure_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, role: str, content: str):
        session = self._sessions.get(session_id)
        if session:
            session.messages.append({"role": role, "content": content})
