"""Tests for the token-counting utility (Gemini primary, tiktoken fallback)."""

from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.core.tokens import _tiktoken_count, count_tokens

SAMPLE_TEXT = "Hello world, this is a test string."


# --- count_tokens: Gemini path ---


async def test_count_tokens_uses_gemini_total_tokens_on_success() -> None:
    mock_response = MagicMock(total_tokens=7)
    mock_client = MagicMock()
    mock_client.aio.models.count_tokens = AsyncMock(return_value=mock_response)

    with patch("pipeline.core.tokens._get_client", return_value=mock_client):
        result = await count_tokens(SAMPLE_TEXT, model="gemini-2.5-flash")

    assert result == 7
    mock_client.aio.models.count_tokens.assert_awaited_once_with(
        model="gemini-2.5-flash",
        contents=SAMPLE_TEXT,
    )


async def test_count_tokens_falls_back_when_gemini_call_raises() -> None:
    mock_client = MagicMock()
    mock_client.aio.models.count_tokens = AsyncMock(side_effect=RuntimeError("API down"))

    with patch("pipeline.core.tokens._get_client", return_value=mock_client):
        result = await count_tokens(SAMPLE_TEXT, model="gemini-2.5-flash")

    assert result > 0


async def test_count_tokens_falls_back_when_model_is_not_a_string() -> None:
    """Mirrors the real wiring risk: a mocked agent's model.id is a MagicMock, not str."""
    result = await count_tokens(SAMPLE_TEXT, model=MagicMock())

    assert result > 0


async def test_count_tokens_falls_back_when_api_key_is_empty() -> None:
    """No mocking needed — genai.Client(api_key='') raises ValueError synchronously."""
    result = await count_tokens(SAMPLE_TEXT, model="gemini-2.5-flash")

    assert result > 0


# --- _tiktoken_count ---


def test_tiktoken_count_returns_nonzero_for_text() -> None:
    assert _tiktoken_count(SAMPLE_TEXT) > 0


def test_tiktoken_count_degrades_to_char_estimate_when_tiktoken_fails() -> None:
    with patch("pipeline.core.tokens.tiktoken.get_encoding", side_effect=RuntimeError("no vocab")):
        result = _tiktoken_count(SAMPLE_TEXT)

    assert result == len(SAMPLE_TEXT) // 4
