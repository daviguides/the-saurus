class ConnectionManager:
    def __init__(self):
        self._sid_to_session: dict[str, str] = {}

    def register(self, sid: str, session_id: str):
        self._sid_to_session[sid] = session_id

    def unregister(self, sid: str):
        self._sid_to_session.pop(sid, None)

    def get_session(self, sid: str) -> str | None:
        return self._sid_to_session.get(sid)
