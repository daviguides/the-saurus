"""Tests for reask(): shared feedback-driven retry helper."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from agno.agent import RunCompletedEvent, RunErrorEvent

from pipeline.agents.parsing import reask


# --- Test model ---


class SampleModel(BaseModel):
    """Simple Pydantic model for testing."""

    name: str
    value: int


VALID_NAME = "test"
VALID_VALUE = 42
ORIGINAL_MESSAGE = "please extract the themes"
FAILURE_DESCRIPTION = "claim_id X is not in the valid set for this batch"


# --- Agno event helpers (mirrors test_parsing.py) ---


def _make_completed_event(content: object) -> RunCompletedEvent:
    """Build a RunCompletedEvent with given content."""
    event = MagicMock(spec=RunCompletedEvent)
    event.content = content
    event.__class__ = RunCompletedEvent
    return event


def _make_error_event(message: str) -> RunErrorEvent:
    """Build a RunErrorEvent."""
    event = MagicMock(spec=RunErrorEvent)
    event.content = message
    event.__class__ = RunErrorEvent
    return event


async def _mock_arun_success(content: object):
    """Async generator simulating successful agent.arun()."""
    yield _make_completed_event(content)


async def _mock_arun_error(message: str):
    """Async generator simulating agent.arun() with error."""
    yield _make_error_event(message)


def _patched_settings(max_retries: int = 2, retry_delay: float = 0.0):
    """Context managers patching the semaphore + settings reask delegates to."""
    return (
        patch("pipeline.agents.models.llm_semaphore", asyncio.Semaphore(1)),
        patch(
            "pipeline.config.settings",
            MagicMock(llm_max_retries=max_retries, llm_retry_delay=retry_delay),
        ),
    )


class TestReask:
    """Test reask()'s feedback-append, attempt-cap, and fallback behavior."""

    async def test_reask_appends_feedback_not_blind_resend(self) -> None:
        """Corrected message differs from original and contains the failure description."""
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "ReaskAgent"
        captured_messages: list[str] = []

        def _arun(message: str, **_kwargs: object):
            captured_messages.append(message)
            return _mock_arun_success(model)

        agent.arun = _arun

        p1, p2 = _patched_settings()
        with p1, p2:
            result = await reask(
                agent, ORIGINAL_MESSAGE, FAILURE_DESCRIPTION, SampleModel,
                fallback=lambda: SampleModel(name="fallback", value=0),
                max_attempts=2, retry_delay=0.0, timeout=5.0,
            )

        assert result.name == VALID_NAME
        assert len(captured_messages) == 1
        assert captured_messages[0] != ORIGINAL_MESSAGE
        assert ORIGINAL_MESSAGE in captured_messages[0]
        assert FAILURE_DESCRIPTION in captured_messages[0]

    async def test_reask_fires_on_injected_failure(self) -> None:
        """First attempt errors, second (still within max_attempts) succeeds."""
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "RetryReaskAgent"
        agent.arun = MagicMock(
            side_effect=[
                _mock_arun_error("transient failure"),
                _mock_arun_success(model),
            ],
        )

        p1, p2 = _patched_settings()
        with p1, p2:
            result = await reask(
                agent, ORIGINAL_MESSAGE, FAILURE_DESCRIPTION, SampleModel,
                fallback=lambda: SampleModel(name="fallback", value=0),
                max_attempts=2, retry_delay=0.0, timeout=5.0,
            )

        assert result.name == VALID_NAME
        assert agent.arun.call_count == 2

    async def test_reask_respects_max_attempts(self) -> None:
        """Agent always errors; exactly max_attempts calls are made."""
        agent = MagicMock()
        agent.name = "AlwaysFailAgent"
        agent.arun = MagicMock(
            side_effect=lambda *_a, **_k: _mock_arun_error("always fails"),
        )

        p1, p2 = _patched_settings()
        with p1, p2:
            await reask(
                agent, ORIGINAL_MESSAGE, FAILURE_DESCRIPTION, SampleModel,
                fallback=lambda: SampleModel(name="fallback", value=0),
                max_attempts=3, retry_delay=0.0, timeout=5.0,
            )

        assert agent.arun.call_count == 3

    async def test_reask_returns_fallback_on_exhaustion(self) -> None:
        """Exhaustion returns the caller-supplied fallback, never raises."""
        agent = MagicMock()
        agent.name = "ExhaustedAgent"
        agent.arun = MagicMock(
            side_effect=lambda *_a, **_k: _mock_arun_error("always fails"),
        )
        fallback_model = SampleModel(name="fallback-used", value=-1)

        p1, p2 = _patched_settings()
        with p1, p2:
            result = await reask(
                agent, ORIGINAL_MESSAGE, FAILURE_DESCRIPTION, SampleModel,
                fallback=lambda: fallback_model,
                max_attempts=2, retry_delay=0.0, timeout=5.0,
            )

        assert result is fallback_model

    async def test_reask_reuses_run_agent_with_retry_semaphore(self) -> None:
        """reask() does not introduce a second concurrency primitive."""
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "SemaphoreAgent"
        agent.arun = MagicMock(return_value=_mock_arun_success(model))

        semaphore = asyncio.Semaphore(1)
        assert semaphore._value == 1

        with patch("pipeline.agents.models.llm_semaphore", semaphore), patch(
            "pipeline.config.settings",
            MagicMock(llm_max_retries=2, llm_retry_delay=0.0),
        ):
            await reask(
                agent, ORIGINAL_MESSAGE, FAILURE_DESCRIPTION, SampleModel,
                fallback=lambda: SampleModel(name="fallback", value=0),
                max_attempts=2, retry_delay=0.0, timeout=5.0,
            )

        # Semaphore released back to its original value: reask went through
        # run_agent_with_retry's single semaphore, not a second one.
        assert semaphore._value == 1

    async def test_reask_success_on_first_corrected_attempt(self) -> None:
        """Happy path: corrected message succeeds immediately, fallback unused."""
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "HappyPathAgent"
        agent.arun = MagicMock(return_value=_mock_arun_success(model))
        fallback_called = False

        def _fallback() -> SampleModel:
            nonlocal fallback_called
            fallback_called = True
            return SampleModel(name="fallback", value=0)

        p1, p2 = _patched_settings()
        with p1, p2:
            result = await reask(
                agent, ORIGINAL_MESSAGE, FAILURE_DESCRIPTION, SampleModel,
                fallback=_fallback,
                max_attempts=2, retry_delay=0.0, timeout=5.0,
            )

        assert result.name == VALID_NAME
        assert agent.arun.call_count == 1
        assert fallback_called is False
