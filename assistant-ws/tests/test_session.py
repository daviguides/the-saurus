"""Tests for assistant_ws.ws.session module."""

import uuid

import pytest

from assistant_ws.ws.session import Session, SessionManager

# --------------- constants ---------------

KNOWN_SESSION_ID = "sess-aaa-111"
OTHER_SESSION_ID = "sess-bbb-222"
UNKNOWN_SESSION_ID = "sess-zzz-999"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
MSG_HELLO = "Hello, world!"
MSG_REPLY = "Hi there!"


# --------------- Session dataclass ---------------


class TestSession:
    """Tests for the Session dataclass."""

    def test_create_with_id(self) -> None:
        """Session stores the given session_id."""
        # Arrange / Act
        session = Session(session_id=KNOWN_SESSION_ID)

        # Assert
        assert session.session_id == KNOWN_SESSION_ID

    def test_default_messages_empty(self) -> None:
        """New session starts with an empty message list."""
        # Arrange / Act
        session = Session(session_id=KNOWN_SESSION_ID)

        # Assert
        assert session.messages == []

    def test_messages_not_shared_between_instances(self) -> None:
        """Each session gets its own message list (no mutable default sharing)."""
        # Arrange
        s1 = Session(session_id="a")
        s2 = Session(session_id="b")

        # Act
        s1.messages.append({"role": ROLE_USER, "content": MSG_HELLO})

        # Assert
        assert len(s1.messages) == 1
        assert len(s2.messages) == 0

    def test_create_with_preloaded_messages(self) -> None:
        """Session can be created with pre-existing messages."""
        # Arrange
        history = [
            {"role": ROLE_USER, "content": MSG_HELLO},
        ]

        # Act
        session = Session(
            session_id=KNOWN_SESSION_ID,
            messages=history,
        )

        # Assert
        assert len(session.messages) == 1
        assert session.messages[0]["content"] == MSG_HELLO


# --------------- SessionManager ---------------


class TestSessionManagerCreate:
    """Tests for SessionManager.create_session."""

    def test_create_returns_uuid(self) -> None:
        """create_session returns a valid UUID string."""
        # Arrange
        mgr = SessionManager()

        # Act
        sid = mgr.create_session()

        # Assert — should parse without error
        uuid.UUID(sid)

    def test_create_stores_session(self) -> None:
        """Created session is retrievable via get_session."""
        # Arrange
        mgr = SessionManager()

        # Act
        sid = mgr.create_session()

        # Assert
        session = mgr.get_session(sid)
        assert session is not None
        assert session.session_id == sid

    def test_create_multiple_unique(self) -> None:
        """Each call produces a distinct session ID."""
        # Arrange
        mgr = SessionManager()

        # Act
        ids = {mgr.create_session() for _ in range(5)}

        # Assert
        assert len(ids) == 5


class TestSessionManagerEnsure:
    """Tests for SessionManager.ensure_session."""

    def test_ensure_creates_new(self) -> None:
        """ensure_session creates a session if it doesn't exist."""
        # Arrange
        mgr = SessionManager()

        # Act
        session = mgr.ensure_session(KNOWN_SESSION_ID)

        # Assert
        assert session.session_id == KNOWN_SESSION_ID
        assert mgr.get_session(KNOWN_SESSION_ID) is session

    def test_ensure_returns_existing(self) -> None:
        """ensure_session returns the same object on repeated calls."""
        # Arrange
        mgr = SessionManager()
        first = mgr.ensure_session(KNOWN_SESSION_ID)
        first.messages.append(
            {"role": ROLE_USER, "content": MSG_HELLO},
        )

        # Act
        second = mgr.ensure_session(KNOWN_SESSION_ID)

        # Assert
        assert first is second
        assert len(second.messages) == 1

    def test_ensure_different_ids_independent(self) -> None:
        """ensure_session with different IDs yields distinct sessions."""
        # Arrange
        mgr = SessionManager()

        # Act
        s1 = mgr.ensure_session(KNOWN_SESSION_ID)
        s2 = mgr.ensure_session(OTHER_SESSION_ID)

        # Assert
        assert s1 is not s2
        assert s1.session_id != s2.session_id


class TestSessionManagerGetSession:
    """Tests for SessionManager.get_session."""

    def test_get_existing(self) -> None:
        """get_session returns the session when it exists."""
        # Arrange
        mgr = SessionManager()
        mgr.ensure_session(KNOWN_SESSION_ID)

        # Act
        result = mgr.get_session(KNOWN_SESSION_ID)

        # Assert
        assert result is not None
        assert result.session_id == KNOWN_SESSION_ID

    def test_get_unknown_returns_none(self) -> None:
        """get_session returns None for an unknown ID."""
        # Arrange
        mgr = SessionManager()

        # Act
        result = mgr.get_session(UNKNOWN_SESSION_ID)

        # Assert
        assert result is None


class TestSessionManagerAddMessage:
    """Tests for SessionManager.add_message."""

    def test_add_message_appends(self) -> None:
        """add_message appends to the session's history."""
        # Arrange
        mgr = SessionManager()
        mgr.ensure_session(KNOWN_SESSION_ID)

        # Act
        mgr.add_message(KNOWN_SESSION_ID, ROLE_USER, MSG_HELLO)

        # Assert
        session = mgr.get_session(KNOWN_SESSION_ID)
        assert session is not None
        assert len(session.messages) == 1
        assert session.messages[0] == {
            "role": ROLE_USER,
            "content": MSG_HELLO,
        }

    def test_add_multiple_messages_preserves_order(self) -> None:
        """Messages are stored in insertion order."""
        # Arrange
        mgr = SessionManager()
        mgr.ensure_session(KNOWN_SESSION_ID)

        # Act
        mgr.add_message(KNOWN_SESSION_ID, ROLE_USER, MSG_HELLO)
        mgr.add_message(
            KNOWN_SESSION_ID,
            ROLE_ASSISTANT,
            MSG_REPLY,
        )

        # Assert
        session = mgr.get_session(KNOWN_SESSION_ID)
        assert session is not None
        assert session.messages[0]["role"] == ROLE_USER
        assert session.messages[1]["role"] == ROLE_ASSISTANT

    def test_add_message_unknown_session_noop(self) -> None:
        """add_message silently does nothing for unknown session."""
        # Arrange
        mgr = SessionManager()

        # Act — should not raise
        mgr.add_message(UNKNOWN_SESSION_ID, ROLE_USER, MSG_HELLO)

        # Assert
        assert mgr.get_session(UNKNOWN_SESSION_ID) is None

    def test_add_message_to_correct_session(self) -> None:
        """Messages go to the specified session only."""
        # Arrange
        mgr = SessionManager()
        mgr.ensure_session(KNOWN_SESSION_ID)
        mgr.ensure_session(OTHER_SESSION_ID)

        # Act
        mgr.add_message(KNOWN_SESSION_ID, ROLE_USER, MSG_HELLO)

        # Assert
        s1 = mgr.get_session(KNOWN_SESSION_ID)
        s2 = mgr.get_session(OTHER_SESSION_ID)
        assert s1 is not None and len(s1.messages) == 1
        assert s2 is not None and len(s2.messages) == 0
