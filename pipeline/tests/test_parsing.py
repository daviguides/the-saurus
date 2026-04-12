"""Tests for parsing module: response parsing, token estimation, retry logic."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from pipeline.agents.parsing import (
    AgentResponseError,
    _ctx_str,
    estimate_tokens,
    parse_agent_response,
    run_agent_with_retry,
)

# --- Constants ---

SAMPLE_TEXT = "Hello world, this is a test string."
SAMPLE_TEXT_LENGTH = len(SAMPLE_TEXT)
CHARS_PER_TOKEN = 4
EXPECTED_TOKENS = SAMPLE_TEXT_LENGTH // CHARS_PER_TOKEN


# --- Test model ---


class SampleModel(BaseModel):
    """Simple Pydantic model for testing parse_agent_response."""

    name: str
    value: int


VALID_NAME = "test"
VALID_VALUE = 42
VALID_JSON = '{"name": "test", "value": 42}'
VALID_DICT = {"name": "test", "value": 42}


# --- estimate_tokens ---


class TestEstimateTokens:
    """Validate rough token estimation from character count."""

    def test_basic_estimate(self) -> None:
        """Estimate is character count divided by 4."""
        # Arrange / Act
        result = estimate_tokens(SAMPLE_TEXT)

        # Assert
        assert result == EXPECTED_TOKENS

    def test_empty_string(self) -> None:
        """Empty string yields zero tokens."""
        assert estimate_tokens("") == 0

    def test_short_string(self) -> None:
        """String shorter than 4 chars yields zero (integer division)."""
        assert estimate_tokens("abc") == 0

    def test_exact_multiple(self) -> None:
        """String of exactly 8 chars yields 2 tokens."""
        assert estimate_tokens("12345678") == 2


# --- _ctx_str ---


class TestCtxStr:
    """Validate context dict formatting for log messages."""

    def test_basic_formatting(self) -> None:
        """Formats key=value pairs separated by spaces."""
        # Arrange
        ctx: dict[str, Any] = {"stage": "analysis", "paper_id": "p1"}

        # Act
        result = _ctx_str(ctx)

        # Assert
        assert "stage=analysis" in result
        assert "paper_id=p1" in result

    def test_excludes_underscore_keys(self) -> None:
        """Keys starting with underscore are excluded."""
        ctx: dict[str, Any] = {
            "stage": "dedup",
            "_emitter": object(),
        }
        result = _ctx_str(ctx)
        assert "_emitter" not in result
        assert "stage=dedup" in result

    def test_empty_dict(self) -> None:
        """Empty dict returns empty string."""
        assert _ctx_str({}) == ""

    def test_all_private_keys(self) -> None:
        """Dict with only private keys returns empty string."""
        ctx: dict[str, Any] = {"_a": 1, "_b": 2}
        assert _ctx_str(ctx) == ""


# --- parse_agent_response ---


class TestParseAgentResponse:
    """Validate parsing of various LLM response formats."""

    def test_already_correct_type(self) -> None:
        """Returns instance directly if already the target model."""
        # Arrange
        model = SampleModel(name=VALID_NAME, value=VALID_VALUE)

        # Act
        result = parse_agent_response(model, SampleModel)

        # Assert
        assert result is model

    def test_dict_input(self) -> None:
        """Parses a plain dict into the model."""
        result = parse_agent_response(VALID_DICT, SampleModel)
        assert result.name == VALID_NAME
        assert result.value == VALID_VALUE

    def test_json_string(self) -> None:
        """Parses a JSON string into the model."""
        result = parse_agent_response(VALID_JSON, SampleModel)
        assert result.name == VALID_NAME
        assert result.value == VALID_VALUE

    def test_markdown_fenced_json(self) -> None:
        """Extracts JSON from markdown code fence."""
        # Arrange
        raw = f"Here is the output:\n```json\n{VALID_JSON}\n```"

        # Act
        result = parse_agent_response(raw, SampleModel)

        # Assert
        assert result.name == VALID_NAME
        assert result.value == VALID_VALUE

    def test_markdown_fenced_no_lang(self) -> None:
        """Extracts JSON from code fence without language specifier."""
        raw = f"Output:\n```\n{VALID_JSON}\n```"
        result = parse_agent_response(raw, SampleModel)
        assert result.name == VALID_NAME

    def test_none_raises(self) -> None:
        """None input raises AgentResponseError."""
        with pytest.raises(AgentResponseError, match="None"):
            parse_agent_response(None, SampleModel)

    def test_empty_string_raises(self) -> None:
        """Empty string raises AgentResponseError."""
        with pytest.raises(AgentResponseError, match="empty string"):
            parse_agent_response("", SampleModel)

    def test_whitespace_only_raises(self) -> None:
        """Whitespace-only string raises AgentResponseError."""
        with pytest.raises(AgentResponseError, match="empty string"):
            parse_agent_response("   \n  ", SampleModel)

    def test_invalid_json_string_raises(self) -> None:
        """Non-JSON string raises a validation error."""
        with pytest.raises(Exception):
            parse_agent_response("not json at all", SampleModel)

    def test_invalid_dict_raises(self) -> None:
        """Dict with wrong fields raises ValidationError."""
        with pytest.raises(Exception):
            parse_agent_response({"wrong": "fields"}, SampleModel)

    def test_json_string_with_surrounding_text(self) -> None:
        """JSON embedded in fenced block with surrounding text is parsed."""
        raw = (
            "I analyzed the data.\n"
            f"```json\n{VALID_JSON}\n```\n"
            "That concludes the analysis."
        )
        result = parse_agent_response(raw, SampleModel)
        assert result.name == VALID_NAME


# --- run_agent_with_retry ---


def _mock_gemini_response(text: str | None) -> MagicMock:
    """Build a mock Gemini API response with given text."""
    part = MagicMock()
    part.text = text

    content = MagicMock()
    content.parts = [part] if text else []

    candidate = MagicMock()
    candidate.content = content
    candidate.finish_reason = "STOP"
    candidate.safety_ratings = None

    response = MagicMock()
    response.candidates = [candidate]
    return response


def _mock_empty_response() -> MagicMock:
    """Build a mock Gemini API response with no candidates."""
    response = MagicMock()
    response.candidates = []
    return response


class TestRunAgentWithRetry:
    """Test retry logic by mocking the Gemini client."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self) -> None:
        """Returns parsed model on first successful API call."""
        # Arrange
        mock_client = MagicMock()
        mock_client.models.generate_content = MagicMock(
            return_value=_mock_gemini_response(VALID_JSON),
        )

        agent = MagicMock()
        agent.name = "TestAgent"
        agent.instructions = "Analyze this."

        with (
            patch(
                "pipeline.agents.parsing._get_gemini_client",
                return_value=mock_client,
            ),
            patch(
                "pipeline.config.settings",
                MagicMock(
                    llm_max_retries=3,
                    llm_retry_delay=0.0,
                    llm_model_id="gemini-test",
                ),
            ),
            patch(
                "pipeline.agents.models.llm_semaphore",
                asyncio.Semaphore(1),
            ),
        ):
            # Act
            result = await run_agent_with_retry(
                agent,
                "test message",
                SampleModel,
                max_retries=1,
                retry_delay=0.0,
                timeout=5.0,
            )

        # Assert
        assert result.name == VALID_NAME
        assert result.value == VALID_VALUE

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self) -> None:
        """Retries after failure and returns on subsequent success."""
        # Arrange
        fail_response = _mock_gemini_response(None)
        fail_response.candidates[0].content.parts = []
        success_response = _mock_gemini_response(VALID_JSON)

        mock_client = MagicMock()
        mock_client.models.generate_content = MagicMock(
            side_effect=[fail_response, success_response],
        )

        agent = MagicMock()
        agent.name = "RetryAgent"
        agent.instructions = "Do the thing."

        max_retries = 3
        with (
            patch(
                "pipeline.agents.parsing._get_gemini_client",
                return_value=mock_client,
            ),
            patch(
                "pipeline.config.settings",
                MagicMock(
                    llm_max_retries=max_retries,
                    llm_retry_delay=0.0,
                    llm_model_id="gemini-test",
                ),
            ),
            patch(
                "pipeline.agents.models.llm_semaphore",
                asyncio.Semaphore(1),
            ),
        ):
            # Act
            result = await run_agent_with_retry(
                agent,
                "test message",
                SampleModel,
                max_retries=max_retries,
                retry_delay=0.0,
                timeout=5.0,
            )

        # Assert
        assert result.name == VALID_NAME
        call_count = mock_client.models.generate_content.call_count
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self) -> None:
        """Raises AgentResponseError after all retries fail."""
        # Arrange
        mock_client = MagicMock()
        mock_client.models.generate_content = MagicMock(
            side_effect=RuntimeError("API down"),
        )

        agent = MagicMock()
        agent.name = "FailAgent"
        agent.instructions = ""

        max_retries = 2
        with (
            patch(
                "pipeline.agents.parsing._get_gemini_client",
                return_value=mock_client,
            ),
            patch(
                "pipeline.config.settings",
                MagicMock(
                    llm_max_retries=max_retries,
                    llm_retry_delay=0.0,
                    llm_model_id="gemini-test",
                ),
            ),
            patch(
                "pipeline.agents.models.llm_semaphore",
                asyncio.Semaphore(1),
            ),
        ):
            # Act / Assert
            with pytest.raises(
                AgentResponseError,
                match="Failed after 2 attempts",
            ):
                await run_agent_with_retry(
                    agent,
                    "test message",
                    SampleModel,
                    max_retries=max_retries,
                    retry_delay=0.0,
                    timeout=5.0,
                )

    @pytest.mark.asyncio
    async def test_empty_response_triggers_retry(self) -> None:
        """Empty Gemini response triggers a retry."""
        # Arrange
        empty_resp = _mock_empty_response()
        success_resp = _mock_gemini_response(VALID_JSON)

        mock_client = MagicMock()
        mock_client.models.generate_content = MagicMock(
            side_effect=[empty_resp, success_resp],
        )

        agent = MagicMock()
        agent.name = "EmptyAgent"
        agent.instructions = "Parse."

        with (
            patch(
                "pipeline.agents.parsing._get_gemini_client",
                return_value=mock_client,
            ),
            patch(
                "pipeline.config.settings",
                MagicMock(
                    llm_max_retries=3,
                    llm_retry_delay=0.0,
                    llm_model_id="gemini-test",
                ),
            ),
            patch(
                "pipeline.agents.models.llm_semaphore",
                asyncio.Semaphore(1),
            ),
        ):
            # Act
            result = await run_agent_with_retry(
                agent,
                "msg",
                SampleModel,
                max_retries=3,
                retry_delay=0.0,
                timeout=5.0,
            )

        # Assert
        assert result.name == VALID_NAME


# --- AgentResponseError ---


class TestAgentResponseError:
    """Validate AgentResponseError is a proper Exception."""

    def test_is_exception(self) -> None:
        """AgentResponseError inherits from Exception."""
        err = AgentResponseError("something broke")
        assert isinstance(err, Exception)
        assert str(err) == "something broke"

    def test_raised_and_caught(self) -> None:
        """Can be raised and caught specifically."""
        with pytest.raises(AgentResponseError):
            raise AgentResponseError("parse failed")
