"""Parse Agno agent responses into Pydantic models with retry logic.

Agno's result.content may be the Pydantic model directly (structured output worked)
or a raw string (LLM returned text). This module handles both cases and provides
retry logic for transient LLM failures.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2.0


class AgentResponseError(Exception):
    """Raised when the agent response cannot be parsed after retries."""


def parse_agent_response(raw: object, model_class: type[T]) -> T:
    """Parse an Agno agent response into the expected Pydantic model."""
    if isinstance(raw, model_class):
        return raw

    if raw is None:
        raise AgentResponseError(f"Agent returned None, expected {model_class.__name__}")

    if isinstance(raw, str):
        cleaned = raw.strip()
        if not cleaned:
            raise AgentResponseError(
                f"Agent returned empty string, expected {model_class.__name__}"
            )
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if json_match:
            cleaned = json_match.group(1).strip()
        return model_class.model_validate_json(cleaned)

    if isinstance(raw, dict):
        return model_class.model_validate(raw)

    return model_class.model_validate_json(str(raw))


async def run_agent_with_retry(
    agent: Any,
    message: str,
    output_schema: type[T],
    *,
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY,
) -> T:
    """Run an Agno agent with retry logic and response parsing."""
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            result = await agent.arun(message, output_schema=output_schema)
            return parse_agent_response(result.content, output_schema)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                logger.warning(
                    "Agent attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt,
                    max_retries,
                    str(exc)[:200],
                    retry_delay * attempt,
                )
                await asyncio.sleep(retry_delay * attempt)
            else:
                logger.error(
                    "Agent failed after %d attempts: %s",
                    max_retries,
                    str(exc)[:200],
                )

    raise AgentResponseError(
        f"Agent failed after {max_retries} attempts: {last_error}"
    )
