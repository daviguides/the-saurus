"""Tests for assistant_ws.ws.connection module."""

import pytest

from assistant_ws.ws.connection import ConnectionManager

# --------------- constants ---------------

SID_ALPHA = "sid-aaa-111"
SID_BETA = "sid-bbb-222"
SID_UNKNOWN = "sid-zzz-999"
SESSION_ONE = "sess-one"
SESSION_TWO = "sess-two"


# --------------- ConnectionManager.register ---------------


class TestConnectionManagerRegister:
    """Tests for ConnectionManager.register."""

    def test_register_stores_mapping(self) -> None:
        """Registered sid maps to the given session_id."""
        # Arrange
        mgr = ConnectionManager()

        # Act
        mgr.register(SID_ALPHA, SESSION_ONE)

        # Assert
        assert mgr.get_session(SID_ALPHA) == SESSION_ONE

    def test_register_multiple_sids(self) -> None:
        """Multiple sids can be registered independently."""
        # Arrange
        mgr = ConnectionManager()

        # Act
        mgr.register(SID_ALPHA, SESSION_ONE)
        mgr.register(SID_BETA, SESSION_TWO)

        # Assert
        assert mgr.get_session(SID_ALPHA) == SESSION_ONE
        assert mgr.get_session(SID_BETA) == SESSION_TWO

    def test_register_overwrites_existing(self) -> None:
        """Re-registering the same sid overwrites the session."""
        # Arrange
        mgr = ConnectionManager()
        mgr.register(SID_ALPHA, SESSION_ONE)

        # Act
        mgr.register(SID_ALPHA, SESSION_TWO)

        # Assert
        assert mgr.get_session(SID_ALPHA) == SESSION_TWO

    def test_multiple_sids_same_session(self) -> None:
        """Different sids can point to the same session_id."""
        # Arrange
        mgr = ConnectionManager()

        # Act
        mgr.register(SID_ALPHA, SESSION_ONE)
        mgr.register(SID_BETA, SESSION_ONE)

        # Assert
        assert mgr.get_session(SID_ALPHA) == SESSION_ONE
        assert mgr.get_session(SID_BETA) == SESSION_ONE


# --------------- ConnectionManager.unregister ---------------


class TestConnectionManagerUnregister:
    """Tests for ConnectionManager.unregister."""

    def test_unregister_removes_mapping(self) -> None:
        """Unregistered sid is no longer retrievable."""
        # Arrange
        mgr = ConnectionManager()
        mgr.register(SID_ALPHA, SESSION_ONE)

        # Act
        mgr.unregister(SID_ALPHA)

        # Assert
        assert mgr.get_session(SID_ALPHA) is None

    def test_unregister_unknown_sid_noop(self) -> None:
        """Unregistering an unknown sid does not raise."""
        # Arrange
        mgr = ConnectionManager()

        # Act / Assert — should not raise
        mgr.unregister(SID_UNKNOWN)

    def test_unregister_does_not_affect_others(self) -> None:
        """Unregistering one sid leaves other mappings intact."""
        # Arrange
        mgr = ConnectionManager()
        mgr.register(SID_ALPHA, SESSION_ONE)
        mgr.register(SID_BETA, SESSION_TWO)

        # Act
        mgr.unregister(SID_ALPHA)

        # Assert
        assert mgr.get_session(SID_ALPHA) is None
        assert mgr.get_session(SID_BETA) == SESSION_TWO

    def test_unregister_then_reregister(self) -> None:
        """A sid can be re-registered after unregistration."""
        # Arrange
        mgr = ConnectionManager()
        mgr.register(SID_ALPHA, SESSION_ONE)
        mgr.unregister(SID_ALPHA)

        # Act
        mgr.register(SID_ALPHA, SESSION_TWO)

        # Assert
        assert mgr.get_session(SID_ALPHA) == SESSION_TWO


# --------------- ConnectionManager.get_session ---------------


class TestConnectionManagerGetSession:
    """Tests for ConnectionManager.get_session."""

    def test_get_registered_sid(self) -> None:
        """get_session returns session_id for a registered sid."""
        # Arrange
        mgr = ConnectionManager()
        mgr.register(SID_ALPHA, SESSION_ONE)

        # Act
        result = mgr.get_session(SID_ALPHA)

        # Assert
        assert result == SESSION_ONE

    def test_get_unregistered_returns_none(self) -> None:
        """get_session returns None for an unknown sid."""
        # Arrange
        mgr = ConnectionManager()

        # Act
        result = mgr.get_session(SID_UNKNOWN)

        # Assert
        assert result is None

    def test_get_after_unregister_returns_none(self) -> None:
        """get_session returns None after the sid is unregistered."""
        # Arrange
        mgr = ConnectionManager()
        mgr.register(SID_ALPHA, SESSION_ONE)
        mgr.unregister(SID_ALPHA)

        # Act
        result = mgr.get_session(SID_ALPHA)

        # Assert
        assert result is None
