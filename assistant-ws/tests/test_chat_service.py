"""Tests for assistant_ws.ws.chat_service module."""

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agno.run.agent import RunEvent
from agno.run.team import TeamRunEvent

from assistant_ws.ws.chat_service import (
    ChatService,
    _team_cache,
    _team_cache_timestamps,
    _session_locks,
    evict_expired_teams,
    evict_team,
    get_or_create_team,
)

# --------------- constants ---------------

SID = "sid-aaa-111"
SESSION_ID = "sess-test-001"


# --------------- helpers ---------------


def _make_sio() -> AsyncMock:
    """Create a mock Socket.IO AsyncServer."""
    sio = AsyncMock()
    sio.emit = AsyncMock()
    return sio


def _make_team_event(event_value: str, content: str | None = None, tool: object | None = None):
    """Build a SimpleNamespace mimicking an Agno stream event."""
    return SimpleNamespace(event=event_value, content=content, tool=tool)


def _token_event(chunk: str):
    return _make_team_event(TeamRunEvent.run_content.value, content=chunk)


def _error_event(msg: str = "something broke"):
    return _make_team_event(TeamRunEvent.run_error.value, content=msg)


def _tool_call_event(tool_name: str = "search_claims"):
    tool = SimpleNamespace(tool_name=tool_name)
    return _make_team_event(RunEvent.tool_call_started.value, tool=tool)


async def _async_iter(items):
    """Turn a list into an async iterator."""
    for item in items:
        yield item


# --------------- fixtures ---------------


@pytest.fixture(autouse=True)
def _clear_caches():
    """Ensure module-level caches are clean before/after each test."""
    _team_cache.clear()
    _team_cache_timestamps.clear()
    _session_locks.clear()
    yield
    _team_cache.clear()
    _team_cache_timestamps.clear()
    _session_locks.clear()


@pytest.fixture()
def sio() -> AsyncMock:
    return _make_sio()


@pytest.fixture()
def service() -> ChatService:
    return ChatService()


@pytest.fixture()
def mock_team() -> AsyncMock:
    team = AsyncMock()
    team.arun = MagicMock()  # returns async generator, configured per test
    return team


# --------------- ChatService.process_message: streaming tokens ---------------


class TestProcessMessageStreaming:
    """process_message streams tokens to the client."""

    @pytest.mark.asyncio
    async def test_tokens_emitted_to_client(self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock) -> None:
        """Each content chunk is emitted as a 'token' event."""
        # Arrange
        chunks = [_token_event("Hello"), _token_event(", world!")]
        mock_team.arun.return_value = _async_iter(chunks)

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            # Act
            await service.process_message(sio, SID, SESSION_ID, "Hi")

        # Assert — two token emits + one done
        token_calls = [c for c in sio.emit.call_args_list if c.args[0] == "token"]
        assert len(token_calls) == 2
        assert token_calls[0].args[1]["content"] == "Hello"
        assert token_calls[1].args[1]["content"] == ", world!"

    @pytest.mark.asyncio
    async def test_tool_call_emits_step_event(self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock) -> None:
        """Tool call events emit a 'step' event with human-readable label."""
        # Arrange
        events = [_tool_call_event("search_claims"), _token_event("result")]
        mock_team.arun.return_value = _async_iter(events)

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            await service.process_message(sio, SID, SESSION_ID, "search for claims")

        step_calls = [c for c in sio.emit.call_args_list if c.args[0] == "step"]
        assert len(step_calls) == 1
        assert "Searching claims" in step_calls[0].args[1]["step"]


# --------------- ChatService.process_message: done event with metrics ---------------


class TestProcessMessageDone:
    """process_message emits a 'done' event with elapsed time metrics."""

    @pytest.mark.asyncio
    async def test_done_event_has_elapsed_ms(self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock) -> None:
        """The 'done' event includes metrics.elapsed_time_ms."""
        # Arrange
        mock_team.arun.return_value = _async_iter([_token_event("ok")])

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            await service.process_message(sio, SID, SESSION_ID, "Hi")

        # Assert
        done_calls = [c for c in sio.emit.call_args_list if c.args[0] == "done"]
        assert len(done_calls) == 1
        metrics = done_calls[0].args[1]["metrics"]
        assert "elapsed_time_ms" in metrics
        assert isinstance(metrics["elapsed_time_ms"], int)
        assert metrics["elapsed_time_ms"] >= 0


# --------------- Concurrent messages: second is rejected ---------------


class TestConcurrentMessageRejection:
    """Concurrent messages to the same session: second is rejected with 'busy' error."""

    @pytest.mark.asyncio
    async def test_second_message_rejected_while_busy(
        self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock
    ) -> None:
        """If a session is already processing, the second call emits an error."""
        # Arrange — first call blocks on a slow stream
        slow_event = asyncio.Event()

        async def _slow_stream(*args, **kwargs):
            yield _token_event("start")
            await slow_event.wait()
            yield _token_event("end")

        mock_team.arun.return_value = _slow_stream()

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            # Act — launch first call (it will block), then fire second
            task1 = asyncio.create_task(service.process_message(sio, SID, SESSION_ID, "first"))
            await asyncio.sleep(0.05)  # let task1 acquire the lock

            await service.process_message(sio, "sid-other", SESSION_ID, "second")

            # Unblock the first call
            slow_event.set()
            await task1

        # Assert — the second call should have produced a busy error
        error_calls = [c for c in sio.emit.call_args_list if c.args[0] == "error"]
        assert any("already in progress" in c.args[1]["message"] for c in error_calls)


# --------------- Session timeout evicts team from cache ---------------


class TestSessionTimeoutEviction:
    """Session timeout evicts team from cache."""

    def test_evict_expired_teams_removes_stale_entries(self) -> None:
        """Teams older than the TTL are evicted."""
        # Arrange — insert a team with an old timestamp
        _team_cache[SESSION_ID] = MagicMock()
        _team_cache_timestamps[SESSION_ID] = time.monotonic() - 99999
        _session_locks[SESSION_ID] = asyncio.Lock()

        # Act
        evict_expired_teams()

        # Assert
        assert SESSION_ID not in _team_cache
        assert SESSION_ID not in _team_cache_timestamps
        assert SESSION_ID not in _session_locks

    def test_evict_expired_keeps_fresh_entries(self) -> None:
        """Teams within the TTL are kept."""
        # Arrange
        _team_cache[SESSION_ID] = MagicMock()
        _team_cache_timestamps[SESSION_ID] = time.monotonic()

        # Act
        evict_expired_teams()

        # Assert
        assert SESSION_ID in _team_cache

    def test_evict_team_removes_specific_session(self) -> None:
        """evict_team removes exactly the specified session."""
        # Arrange
        other_session = "sess-other"
        _team_cache[SESSION_ID] = MagicMock()
        _team_cache_timestamps[SESSION_ID] = time.monotonic()
        _team_cache[other_session] = MagicMock()
        _team_cache_timestamps[other_session] = time.monotonic()

        # Act
        evict_team(SESSION_ID)

        # Assert
        assert SESSION_ID not in _team_cache
        assert other_session in _team_cache


# --------------- MCP tools unavailable: graceful degradation ---------------


class TestMCPToolsUnavailable:
    """When MCP tools are unavailable, the assistant degrades gracefully."""

    @pytest.mark.asyncio
    async def test_team_build_failure_emits_error(self, sio: AsyncMock, service: ChatService) -> None:
        """If build_coordinator_team fails (e.g. MCP unreachable), an error event is emitted."""
        with patch(
            "assistant_ws.ws.chat_service.get_or_create_team",
            side_effect=ConnectionError("MCP server unreachable"),
        ):
            await service.process_message(sio, SID, SESSION_ID, "Hello")

        error_calls = [c for c in sio.emit.call_args_list if c.args[0] == "error"]
        assert len(error_calls) == 1
        assert "internal error" in error_calls[0].args[1]["message"].lower()

    @pytest.mark.asyncio
    async def test_tool_call_error_does_not_crash(
        self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock
    ) -> None:
        """A tool call that errors still allows the stream to continue if the team handles it."""
        # Simulate: tool call event, then a normal token (team recovered from tool error)
        events = [
            _tool_call_event("get_paper_themes"),
            _token_event("I could not retrieve themes, but here is what I know."),
        ]
        mock_team.arun.return_value = _async_iter(events)

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            await service.process_message(sio, SID, SESSION_ID, "What themes?")

        # Should still emit done (no crash)
        done_calls = [c for c in sio.emit.call_args_list if c.args[0] == "done"]
        assert len(done_calls) == 1


# --------------- Empty message is rejected ---------------


class TestEmptyMessageRejection:
    """Empty message handling (validated at events.py layer, tested via ChatService robustness)."""

    @pytest.mark.asyncio
    async def test_empty_text_still_calls_team(self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock) -> None:
        """ChatService itself does not reject empty text — that's events.py's job.

        But we verify it doesn't crash if an empty string somehow reaches it.
        """
        mock_team.arun.return_value = _async_iter([])

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            await service.process_message(sio, SID, SESSION_ID, "")

        # Should emit done without crashing
        done_calls = [c for c in sio.emit.call_args_list if c.args[0] == "done"]
        assert len(done_calls) == 1


# --------------- Message exceeding length limit is rejected ---------------


class TestMessageLengthLimit:
    """Message length validation (events.py layer, but we test ChatService robustness)."""

    @pytest.mark.asyncio
    async def test_very_long_message_does_not_crash(
        self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock
    ) -> None:
        """ChatService does not enforce length limits, but must not crash on long input."""
        long_text = "x" * 50000
        mock_team.arun.return_value = _async_iter([_token_event("ok")])

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            await service.process_message(sio, SID, SESSION_ID, long_text)

        done_calls = [c for c in sio.emit.call_args_list if c.args[0] == "done"]
        assert len(done_calls) == 1


# --------------- Error during team.arun: error event emitted ---------------


class TestTeamRunError:
    """Error during team.arun: error event emitted to client."""

    @pytest.mark.asyncio
    async def test_run_error_event_emits_error_to_client(
        self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock
    ) -> None:
        """A TeamRunEvent.run_error in the stream emits an error event and returns early."""
        events = [_token_event("partial"), _error_event("LLM quota exceeded")]
        mock_team.arun.return_value = _async_iter(events)

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            await service.process_message(sio, SID, SESSION_ID, "Hello")

        error_calls = [c for c in sio.emit.call_args_list if c.args[0] == "error"]
        assert len(error_calls) == 1
        assert "error occurred" in error_calls[0].args[1]["message"].lower()

        # No done event should be emitted after a run error
        done_calls = [c for c in sio.emit.call_args_list if c.args[0] == "done"]
        assert len(done_calls) == 0

    @pytest.mark.asyncio
    async def test_exception_during_arun_emits_error(
        self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock
    ) -> None:
        """An unhandled exception from team.arun emits an error event."""

        async def _exploding_stream(*args, **kwargs):
            yield _token_event("partial")
            raise RuntimeError("unexpected LLM failure")

        mock_team.arun.return_value = _exploding_stream()

        with patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team):
            await service.process_message(sio, SID, SESSION_ID, "Hello")

        error_calls = [c for c in sio.emit.call_args_list if c.args[0] == "error"]
        assert len(error_calls) == 1
        assert "internal error" in error_calls[0].args[1]["message"].lower()

    @pytest.mark.asyncio
    async def test_timeout_emits_error(self, sio: AsyncMock, service: ChatService, mock_team: AsyncMock) -> None:
        """A timeout during team.arun emits a timeout error event."""

        async def _hanging_stream(*args, **kwargs):
            yield _token_event("start")
            await asyncio.sleep(9999)

        mock_team.arun.return_value = _hanging_stream()

        with (
            patch("assistant_ws.ws.chat_service.get_or_create_team", return_value=mock_team),
            patch("assistant_ws.ws.chat_service.settings") as mock_settings,
        ):
            mock_settings.team_run_timeout_seconds = 0.1
            await service.process_message(sio, SID, SESSION_ID, "Hello")

        error_calls = [c for c in sio.emit.call_args_list if c.args[0] == "error"]
        assert len(error_calls) == 1
        assert "timed out" in error_calls[0].args[1]["message"].lower()
