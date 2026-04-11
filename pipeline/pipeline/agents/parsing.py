"""Parse Agno agent responses into Pydantic models with retry logic and observability.

Agno's result.content may be the Pydantic model directly (structured output worked)
or a raw string (LLM returned text). This module handles both cases and provides
retry logic for transient LLM failures.

Uses Agno streaming mode (arun with stream=True, stream_events=True) to capture
granular agent lifecycle events (RunStarted, RunContent, ToolCall, RunCompleted, etc.)
while preserving identical retry, timeout, and parse behavior.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

LLM_TIMEOUT = 180.0  # seconds — structured output for large papers needs more time


class AgentResponseError(Exception):
    """Raised when the agent response cannot be parsed after retries."""


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


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
    max_retries: int | None = None,
    retry_delay: float | None = None,
    timeout: float = LLM_TIMEOUT,
    context: dict[str, Any] | None = None,
    on_event: Callable[[Any], Awaitable[None]] | None = None,
) -> T:
    """Run an Agno agent with retry logic, timeout, and response parsing.

    Uses non-streaming mode to avoid Agno's per-chunk JSON parsing bug
    that silently fails on large responses (>100K chars).

    Args:
        agent: Agno Agent instance.
        message: The prompt message to send.
        output_schema: Pydantic model class for structured output.
        max_retries: Number of retry attempts.
        retry_delay: Base delay between retries (multiplied by attempt number).
        timeout: Max seconds to wait for a single LLM call.
        context: Optional dict with debug info (paper_id, stage, etc.) for logging.
        on_event: Unused (kept for API compat). Streaming disabled.
    """
    from pipeline.agents.models import llm_semaphore
    from pipeline.config import settings

    if max_retries is None:
        max_retries = settings.llm_max_retries
    if retry_delay is None:
        retry_delay = settings.llm_retry_delay

    ctx = context or {}

    # Resolve raw response dump directory from context
    job_dir: Path | None = None
    if ctx.get("job_dir"):
        job_dir = Path(ctx["job_dir"]) / "raw"
    agent_name = getattr(agent, "name", agent.__class__.__name__)
    msg_chars = len(message)
    msg_tokens = estimate_tokens(message)

    logger.info(
        "[%s] Starting (stream) | input_chars=%d input_tokens=~%d schema=%s %s",
        agent_name,
        msg_chars,
        msg_tokens,
        output_schema.__name__,
        " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "",
    )

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        t0 = time.monotonic()
        try:
            async with llm_semaphore:
                logger.info(
                    "[%s] Acquired semaphore (attempt %d/%d) %s",
                    agent_name, attempt, max_retries,
                    " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "",
                )
                async with asyncio.timeout(timeout):
                    result = await agent.arun(
                        message,
                        stream=False,
                        output_schema=output_schema,
                    )
                raw = result.content

            elapsed = time.monotonic() - t0

            # Log raw response type and size
            raw_type = type(raw).__name__
            raw_len = len(str(raw)) if raw else 0
            logger.info(
                "[%s] LLM responded | attempt=%d/%d elapsed=%.1fs type=%s len=%d %s",
                agent_name,
                attempt,
                max_retries,
                elapsed,
                raw_type,
                raw_len,
                " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "",
            )

            if raw is None or (isinstance(raw, str) and not raw.strip()):
                logger.warning(
                    "[%s] LLM returned empty/None | attempt=%d/%d elapsed=%.1fs %s",
                    agent_name,
                    attempt,
                    max_retries,
                    elapsed,
                    " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "",
                )

            # Save raw response for debugging
            if job_dir and raw is not None:
                try:
                    job_dir.mkdir(parents=True, exist_ok=True)
                    paper_id = ctx.get("paper_id", "unknown")
                    stage = ctx.get("stage", agent_name)
                    filename = f"{paper_id}_{stage}_attempt{attempt}.txt"
                    (job_dir / filename).write_text(str(raw)[:500_000])
                except Exception:
                    pass  # never fail on debug saves

            parsed = parse_agent_response(raw, output_schema)
            logger.info(
                "[%s] Parsed OK | attempt=%d/%d elapsed=%.1fs %s",
                agent_name,
                attempt,
                max_retries,
                elapsed,
                " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "",
            )
            return parsed

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - t0
            last_error = TimeoutError(f"LLM call timed out after {timeout}s")
            logger.error(
                "[%s] TIMEOUT | attempt=%d/%d elapsed=%.1fs timeout=%.0fs %s",
                agent_name,
                attempt,
                max_retries,
                elapsed,
                timeout,
                " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "",
            )

        except Exception as exc:
            elapsed = time.monotonic() - t0
            last_error = exc
            logger.error(
                "[%s] ERROR | attempt=%d/%d elapsed=%.1fs error=%s %s",
                agent_name,
                attempt,
                max_retries,
                elapsed,
                str(exc)[:300],
                " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "",
            )

        if attempt < max_retries:
            wait = retry_delay * attempt
            logger.info(
                "[%s] Retrying in %.1fs (attempt %d/%d) %s",
                agent_name,
                wait,
                attempt + 1,
                max_retries,
                " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "",
            )
            await asyncio.sleep(wait)

    raise AgentResponseError(
        f"[{agent_name}] Failed after {max_retries} attempts: {last_error}"
    )
