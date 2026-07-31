"""Tests for parsing module: token estimation and retry logic."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agno.agent import RunCompletedEvent, RunErrorEvent
from pydantic import BaseModel

from pipeline.agents.parsing import (
    AgentResponseError,
    estimate_tokens,
    run_agent_with_retry,
)

# --- Constants ---

SAMPLE_TEXT = "Hello world, this is a test string."
SAMPLE_TEXT_LENGTH = len(SAMPLE_TEXT)
CHARS_PER_TOKEN = 4
EXPECTED_TOKENS = SAMPLE_TEXT_LENGTH // CHARS_PER_TOKEN


# --- Test model ---


class SampleModel(BaseModel):
    """Simple Pydantic model for testing."""

    name: str
    value: int


VALID_NAME = "test"
VALID_VALUE = 42


# --- estimate_tokens ---


class TestEstimateTokens:
    """Validate rough token estimation from character count."""

    def test_basic_estimate(self) -> None:
        """Estimate is character count divided by 4."""
        result = estimate_tokens(SAMPLE_TEXT)
        assert result == EXPECTED_TOKENS

    def test_empty_string(self) -> None:
        """Empty string yields zero tokens."""
        assert estimate_tokens("") == 0

    def test_short_string(self) -> None:
        """String shorter than 4 chars yields zero."""
        assert estimate_tokens("abc") == 0

    def test_exact_multiple(self) -> None:
        """String of exactly 8 chars yields 2 tokens."""
        assert estimate_tokens("12345678") == 2


# --- Agno event helpers ---


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


async def _mock_arun_empty():
    """Async generator simulating agent.arun() with no events."""
    return
    yield  # noqa: make it an async generator


async def _mock_arun_exception(exc: Exception):
    """Async generator that raises an exception."""
    raise exc
    yield  # noqa: make it an async generator


# --- run_agent_with_retry ---


class TestRunAgentWithRetry:
    """Test retry logic by mocking agent.arun()."""

    async def test_success_on_first_attempt(self) -> None:
        """Returns parsed model on first successful call."""
        # Arrange
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "TestAgent"
        agent.arun = MagicMock(
            return_value=_mock_arun_success(model),
        )

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=3,
                llm_retry_delay=0.0,
            ),
        ):
            # Act
            result = await run_agent_with_retry(
                agent, "test message", SampleModel,
                max_retries=1, retry_delay=0.0, timeout=5.0,
            )

        # Assert
        assert result.name == VALID_NAME
        assert result.value == VALID_VALUE

    async def test_dict_content_validated(self) -> None:
        """Dict content is validated against output schema."""
        # Arrange
        agent = MagicMock()
        agent.name = "DictAgent"
        agent.arun = MagicMock(
            return_value=_mock_arun_success(
                {"name": VALID_NAME, "value": VALID_VALUE},
            ),
        )

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=1,
                llm_retry_delay=0.0,
            ),
        ):
            result = await run_agent_with_retry(
                agent, "msg", SampleModel,
                max_retries=1, retry_delay=0.0, timeout=5.0,
            )

        assert result.name == VALID_NAME
        assert result.value == VALID_VALUE

    async def test_retries_on_error_event(self) -> None:
        """Retries when agent returns RunErrorEvent."""
        # Arrange
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "RetryAgent"
        agent.arun = MagicMock(
            side_effect=[
                _mock_arun_error("LLM failed"),
                _mock_arun_success(model),
            ],
        )

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=3,
                llm_retry_delay=0.0,
            ),
        ):
            result = await run_agent_with_retry(
                agent, "msg", SampleModel,
                max_retries=3, retry_delay=0.0, timeout=5.0,
            )

        assert result.name == VALID_NAME
        assert agent.arun.call_count == 2

    async def test_retries_on_empty_response(self) -> None:
        """Retries when agent returns no events."""
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "EmptyAgent"
        agent.arun = MagicMock(
            side_effect=[
                _mock_arun_empty(),
                _mock_arun_success(model),
            ],
        )

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=3,
                llm_retry_delay=0.0,
            ),
        ):
            result = await run_agent_with_retry(
                agent, "msg", SampleModel,
                max_retries=3, retry_delay=0.0, timeout=5.0,
            )

        assert result.name == VALID_NAME

    async def test_raises_after_all_retries_exhausted(self) -> None:
        """Raises AgentResponseError after all retries fail."""
        agent = MagicMock()
        agent.name = "FailAgent"
        agent.arun = MagicMock(
            side_effect=RuntimeError("API down"),
        )

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=2,
                llm_retry_delay=0.0,
            ),
        ):
            with pytest.raises(
                AgentResponseError,
                match="failed after 2 attempts",
            ):
                await run_agent_with_retry(
                    agent, "msg", SampleModel,
                    max_retries=2, retry_delay=0.0, timeout=5.0,
                )

    async def test_reasks_on_validation_error(self) -> None:
        """Schema-parse failure feeds the validation detail into the next attempt
        instead of blind-resending the identical message."""
        agent = MagicMock()
        agent.name = "SchemaAgent"
        agent.arun = MagicMock(
            side_effect=[
                _mock_arun_success({"name": VALID_NAME}),  # missing 'value' -> ValidationError
                _mock_arun_success({"name": VALID_NAME, "value": VALID_VALUE}),
            ],
        )

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=3,
                llm_retry_delay=0.0,
            ),
        ):
            result = await run_agent_with_retry(
                agent, "original message", SampleModel,
                max_retries=3, retry_delay=0.0, timeout=5.0,
            )

        assert result.name == VALID_NAME
        assert result.value == VALID_VALUE
        assert agent.arun.call_count == 2

        first_message = agent.arun.call_args_list[0].args[0]
        second_message = agent.arun.call_args_list[1].args[0]
        assert first_message == "original message"
        assert second_message != first_message
        assert "original message" in second_message
        assert "issue" in second_message

    async def test_raises_after_all_retries_exhausted_on_validation_error(self) -> None:
        """Persistent schema failure still raises AgentResponseError after max_retries."""
        agent = MagicMock()
        agent.name = "AlwaysInvalidAgent"
        agent.arun = MagicMock(
            side_effect=lambda *args, **kwargs: _mock_arun_success(
                {"name": VALID_NAME},  # always missing 'value'
            ),
        )

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=2,
                llm_retry_delay=0.0,
            ),
        ):
            with pytest.raises(
                AgentResponseError,
                match="failed after 2 attempts",
            ):
                await run_agent_with_retry(
                    agent, "msg", SampleModel,
                    max_retries=2, retry_delay=0.0, timeout=5.0,
                )

        assert agent.arun.call_count == 2

    async def test_calls_count_tokens_with_message(self) -> None:
        """input_tokens is sourced from count_tokens, not the char/4 heuristic."""
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "TokenAgent"
        agent.arun = MagicMock(
            return_value=_mock_arun_success(model),
        )

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=1,
                llm_retry_delay=0.0,
            ),
        ), patch(
            "pipeline.core.tokens.count_tokens",
            AsyncMock(return_value=99),
        ) as mock_count_tokens:
            await run_agent_with_retry(
                agent, "test message", SampleModel,
                max_retries=1, retry_delay=0.0, timeout=5.0,
            )

        mock_count_tokens.assert_awaited_once_with("test message")

    async def test_forwards_events_to_callback(self) -> None:
        """Events are forwarded to the on_event callback."""
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)
        agent = MagicMock()
        agent.name = "EventAgent"
        agent.arun = MagicMock(
            return_value=_mock_arun_success(model),
        )

        received_events: list = []

        async def callback(event):
            received_events.append(event)

        with patch(
            "pipeline.agents.models.llm_semaphore",
            asyncio.Semaphore(1),
        ), patch(
            "pipeline.config.settings",
            MagicMock(
                llm_max_retries=1,
                llm_retry_delay=0.0,
            ),
        ):
            await run_agent_with_retry(
                agent, "msg", SampleModel,
                max_retries=1, retry_delay=0.0, timeout=5.0,
                on_event=callback,
            )

        assert len(received_events) == 1


# --- AgentResponseError ---


class TestAgentResponseError:
    """Validate AgentResponseError is a proper Exception."""

    def test_is_exception(self) -> None:
        """AgentResponseError inherits from Exception and AgentError."""
        from pipeline.core.exceptions import AgentError

        err = AgentResponseError("something broke")
        assert isinstance(err, Exception)
        assert isinstance(err, AgentError)
        assert str(err) == "something broke"
        assert err.agent_name == "unknown"

    def test_raised_and_caught(self) -> None:
        """Can be raised and caught specifically."""
        with pytest.raises(AgentResponseError):
            raise AgentResponseError("parse failed")
