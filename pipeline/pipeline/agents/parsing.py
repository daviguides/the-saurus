"""Run Agno agents with retry logic and observability."""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

from agno.agent import Agent as AgnoAgent
from agno.agent import RunCompletedEvent, RunErrorEvent
from pydantic import BaseModel

from pipeline.core.exceptions import AgentError

logger = logging.getLogger(__name__)


LLM_TIMEOUT = 300.0  # seconds


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    CHARS_PER_TOKEN = 4
    return len(text) // CHARS_PER_TOKEN


class AgentResponseError(AgentError):
    """Raised when agent produces invalid or empty response."""

    def __init__(self, message: str, agent_name: str = "unknown") -> None:
        super().__init__(message, agent_name=agent_name)


async def run_agent_with_retry[T: BaseModel](
    agent: AgnoAgent,
    message: str,
    output_schema: type[T],
    *,
    max_retries: int | None = None,
    retry_delay: float | None = None,
    timeout: float = LLM_TIMEOUT,
    context: dict[str, Any] | None = None,
    on_event: Callable[[Any], Awaitable[None]] | None = None,
) -> T:
    """Run Agno agent with retry logic, timeout, and event streaming.

    Uses agent.arun() with streaming to capture granular lifecycle
    events (started, content, tool_call, completed, error).
    """
    from pipeline.agents.models import llm_semaphore
    from pipeline.config import settings
    from pipeline.core.tokens import count_tokens

    if max_retries is None:
        max_retries = settings.llm_max_retries
    if retry_delay is None:
        retry_delay = settings.llm_retry_delay

    ctx = context or {}
    agent_name = agent.name or agent.__class__.__name__
    stage = ctx.get("stage", "")
    paper_id = ctx.get("paper_id", "")

    input_tokens = await count_tokens(message)
    logger.info(
        "Starting %s (stream) | input_chars=%d input_tokens=%d stage=%s",
        agent_name, len(message), input_tokens, stage,
    )

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            async with llm_semaphore:
                logger.info(
                    "%s Acquired semaphore (attempt %d/%d) paper_id=%s stage=%s",
                    agent_name, attempt, max_retries, paper_id, stage,
                )

                async with asyncio.timeout(timeout):
                    result_content: T | None = None
                    run_error: str | None = None

                    response_stream = agent.arun(
                        message,
                        stream=True,
                        stream_events=True,
                    )

                    async for event in response_stream:
                        # Forward all events to the callback
                        if on_event is not None:
                            try:
                                await on_event(event)
                            except Exception:
                                logger.debug(
                                    "Event callback error", exc_info=True,
                                )

                        if isinstance(event, RunCompletedEvent):
                            result_content = event.content
                        elif isinstance(event, RunErrorEvent):
                            run_error = str(event.content) if event.content else "Unknown error"

                    if run_error:
                        raise AgentResponseError(
                            f"{agent_name} returned error: {run_error}",
                            agent_name=agent_name,
                        )

                    if result_content is None:
                        raise AgentResponseError(
                            f"{agent_name} returned empty response",
                            agent_name=agent_name,
                        )

                    # Validate against output schema if needed
                    if isinstance(result_content, output_schema):
                        return result_content
                    elif isinstance(result_content, dict):
                        return output_schema.model_validate(result_content)
                    elif isinstance(result_content, str):
                        return output_schema.model_validate_json(result_content)
                    else:
                        return output_schema.model_validate(result_content)

        except TimeoutError:
            last_error = TimeoutError(
                f"{agent_name} timed out after {timeout}s"
            )
            logger.warning(
                "%s timed out (attempt %d/%d)",
                agent_name, attempt, max_retries,
            )
        except AgentResponseError as e:
            last_error = e
            logger.warning(
                "%s response error (attempt %d/%d): %s",
                agent_name, attempt, max_retries, e,
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "%s unexpected error (attempt %d/%d): %s",
                agent_name, attempt, max_retries, e,
            )

        if attempt < max_retries:
            # B7: Exponential backoff with jitter
            delay = retry_delay * (2 ** (attempt - 1)) + random.uniform(0, retry_delay * 0.5)
            logger.info(
                "%s retrying in %.1fs...", agent_name, delay,
            )
            await asyncio.sleep(delay)

    raise AgentResponseError(
        f"{agent_name} failed after {max_retries} attempts: {last_error}",
        agent_name=agent_name,
    )


async def reask[T: BaseModel](
    agent: AgnoAgent,
    message: str,
    failure_description: str,
    output_schema: type[T],
    fallback: Callable[[], T],
    *,
    max_attempts: int = 2,
    retry_delay: float | None = None,
    timeout: float = LLM_TIMEOUT,
    context: dict[str, Any] | None = None,
    on_event: Callable[[Any], Awaitable[None]] | None = None,
) -> T:
    """Re-invoke agent with failure feedback appended; fall back on exhaustion.

    Extends run_agent_with_retry rather than duplicating its semaphore/
    timeout/backoff loop: the corrected message is sent through that same
    retry loop capped at max_attempts, so a single shared mechanism backs
    every detection point that needs feedback-driven correction.
    """
    corrected_message = (
        f"{message}\n\n"
        f"Your previous response had an issue: {failure_description}\n"
        f"Please correct this and provide a valid response."
    )

    agent_name = agent.name or agent.__class__.__name__

    try:
        return await run_agent_with_retry(
            agent,
            corrected_message,
            output_schema,
            max_retries=max_attempts,
            retry_delay=retry_delay,
            timeout=timeout,
            context=context,
            on_event=on_event,
        )
    except AgentResponseError:
        logger.warning(
            "%s reask exhausted after %d attempts, using fallback",
            agent_name, max_attempts,
        )
        return fallback()
