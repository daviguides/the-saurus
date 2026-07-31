"""Token counting utility: Gemini count_tokens primary, tiktoken fallback."""

from __future__ import annotations

import logging

import tiktoken
from google import genai

logger = logging.getLogger(__name__)

_FALLBACK_ENCODING_NAME = "cl100k_base"
_CHARS_PER_TOKEN_FALLBACK = 4

_client: genai.Client | None = None


def _tiktoken_count(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding(_FALLBACK_ENCODING_NAME)
        return len(encoding.encode(text))
    except Exception:
        logger.warning("tiktoken fallback failed, using char-based estimate", exc_info=True)
        return len(text) // _CHARS_PER_TOKEN_FALLBACK


def _get_client(api_key: str) -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=api_key or None)
    return _client


async def count_tokens(text: str, model: str | None = None) -> int:
    """Count tokens via Gemini's count_tokens API; fall back to tiktoken.

    Fallback triggers on missing/invalid API key, an invalid model id,
    or any Gemini-call failure (offline, rate-limited, non-Gemini model).
    Never raises — worst case returns a char-based estimate.
    """
    from pipeline.config import settings

    resolved_model = model if isinstance(model, str) and model else settings.llm_model_id
    if not isinstance(resolved_model, str) or not resolved_model:
        return _tiktoken_count(text)

    try:
        client = _get_client(settings.llm_api_key)
        response = await client.aio.models.count_tokens(model=resolved_model, contents=text)
        return response.total_tokens or 0
    except Exception:
        logger.warning(
            "Gemini count_tokens failed for model=%s, falling back to tiktoken",
            resolved_model,
            exc_info=True,
        )
        return _tiktoken_count(text)
