"""Parse Agno agent responses into Pydantic models with retry logic and observability.

Agno's result.content may be the Pydantic model directly (structured output worked)
or a raw string (LLM returned text). This module handles both cases and provides
retry logic for transient LLM failures.

Uses non-streaming mode to avoid Agno's per-chunk JSON parsing bug on large responses.
Emits synthetic agent events (started/completed/error) through the pipeline EventEmitter.
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

LLM_TIMEOUT = 180.0  # seconds
DIRECT_FALLBACK_ENABLED = True  # Bypass Agno on empty response and call Gemini directly


class AgentResponseError(Exception):
    """Raised when the agent response cannot be parsed after retries."""


async def _direct_gemini_call(message: str, instructions: str, agent_name: str, ctx: dict) -> str | None:
    """Fallback: call Gemini API directly, bypassing Agno.

    Used when Agno returns empty content (silently swallowed error).
    Returns the raw text response or None on failure.
    """
    try:
        import google.genai as genai
        from pipeline.config import settings

        client = genai.Client(api_key=settings.llm_api_key)
        full_prompt = f"{instructions}\n\n{message}"

        logger.info(
            "[%s] DIRECT FALLBACK — calling Gemini API directly (bypassing Agno) %s",
            agent_name,
            " ".join(f"{k}={v}" for k, v in ctx.items() if k not in ("_emitter", "job_dir")) if ctx else "",
        )

        result = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.llm_model_id,
            contents=full_prompt,
        )

        if result.candidates:
            candidate = result.candidates[0]
            if candidate.content and candidate.content.parts:
                text = candidate.content.parts[0].text
                logger.info(
                    "[%s] DIRECT FALLBACK succeeded | len=%d finish=%s %s",
                    agent_name, len(text), candidate.finish_reason,
                    " ".join(f"{k}={v}" for k, v in ctx.items() if k not in ("_emitter", "job_dir")) if ctx else "",
                )
                return text
            else:
                logger.error(
                    "[%s] DIRECT FALLBACK — no content | finish=%s safety=%s",
                    agent_name, candidate.finish_reason, candidate.safety_ratings,
                )
        else:
            logger.error(
                "[%s] DIRECT FALLBACK — no candidates | feedback=%s",
                agent_name, getattr(result, "prompt_feedback", None),
            )
    except Exception as exc:
        logger.error("[%s] DIRECT FALLBACK failed: %s", agent_name, str(exc)[:300])

    return None


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


async def _emit_event(
    on_event: Callable[[Any], Awaitable[None]] | None,
    event_type: str,
    agent_name: str,
    ctx: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a synthetic agent event through the event bridge callback."""
    if on_event is None:
        return
    from pipeline.agents.step_messages import get_step_message, get_technical_message
    from pipeline.core.events import Event, EventType

    payload: dict[str, Any] = {
        "agent_name": agent_name,
        "stage": ctx.get("stage", ""),
    }
    if ctx.get("paper_id"):
        payload["paper_id"] = ctx["paper_id"]
    if extra:
        payload.update(extra)

    payload["message"] = get_step_message(event_type, agent_name, ctx)
    payload["technical_message"] = get_technical_message(event_type, agent_name, payload)

    # Map string to EventType enum
    event_type_enum = getattr(EventType, event_type.upper(), event_type)

    try:
        # The on_event callback from event_bridge expects Agno events,
        # but we're emitting directly via the emitter from context
        emitter = ctx.get("_emitter")
        if emitter:
            await emitter.emit(event_type_enum, payload)
    except Exception:
        logger.warning("[%s] Failed to emit synthetic %s event", agent_name, event_type)


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

    Emits synthetic agent events (started/completed/error) for the frontend
    Event Trace, replacing the Agno streaming events we can't use.
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
        "[%s] Starting | input_chars=%d input_tokens=~%d schema=%s %s",
        agent_name,
        msg_chars,
        msg_tokens,
        output_schema.__name__,
        " ".join(f"{k}={v}" for k, v in ctx.items() if k != "_emitter") if ctx else "",
    )

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        t0 = time.monotonic()

        # Emit agent_started
        await _emit_event(on_event, "agent_started", agent_name, ctx, {
            "model": getattr(getattr(agent, "model", None), "id", ""),
            "input_tokens": msg_tokens,
            "attempt": attempt,
        })

        try:
            async with llm_semaphore:
                logger.info(
                    "[%s] Acquired semaphore (attempt %d/%d) %s",
                    agent_name, attempt, max_retries,
                    " ".join(f"{k}={v}" for k, v in ctx.items() if k != "_emitter") if ctx else "",
                )
                async with asyncio.timeout(timeout):
                    result = await agent.arun(
                        message,
                        stream=False,
                        output_schema=output_schema,
                    )
                raw = result.content

            elapsed = time.monotonic() - t0
            elapsed_ms = int(elapsed * 1000)

            # Log raw response type and size
            raw_type = type(raw).__name__
            raw_len = len(str(raw)) if raw else 0
            logger.info(
                "[%s] LLM responded | attempt=%d/%d elapsed=%.1fs type=%s len=%d %s",
                agent_name, attempt, max_retries, elapsed, raw_type, raw_len,
                " ".join(f"{k}={v}" for k, v in ctx.items() if k != "_emitter") if ctx else "",
            )

            if raw is None or (isinstance(raw, str) and not raw.strip()):
                logger.warning(
                    "[%s] LLM returned empty/None | attempt=%d/%d elapsed=%.1fs %s",
                    agent_name, attempt, max_retries, elapsed,
                    " ".join(f"{k}={v}" for k, v in ctx.items() if k != "_emitter") if ctx else "",
                )

                # Fallback: call Gemini directly when Agno silently fails
                if DIRECT_FALLBACK_ENABLED:
                    instructions = getattr(agent, "instructions", "") or ""
                    if not instructions:
                        instructions = getattr(getattr(agent, "_agent", agent), "instructions", "") or ""
                    direct_raw = await _direct_gemini_call(message, instructions, agent_name, ctx)
                    if direct_raw:
                        raw = direct_raw

            # Save raw response for debugging
            if job_dir and raw is not None:
                try:
                    job_dir.mkdir(parents=True, exist_ok=True)
                    paper_id = ctx.get("paper_id", "unknown")
                    stage = ctx.get("stage", agent_name)
                    filename = f"{paper_id}_{stage}_attempt{attempt}.txt"
                    (job_dir / filename).write_text(str(raw)[:500_000])
                except Exception:
                    pass

            parsed = parse_agent_response(raw, output_schema)
            logger.info(
                "[%s] Parsed OK | attempt=%d/%d elapsed=%.1fs %s",
                agent_name, attempt, max_retries, elapsed,
                " ".join(f"{k}={v}" for k, v in ctx.items() if k != "_emitter") if ctx else "",
            )

            # Emit agent_completed
            await _emit_event(on_event, "agent_completed", agent_name, ctx, {
                "elapsed_ms": elapsed_ms,
                "response_len": raw_len,
            })

            return parsed

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - t0
            last_error = TimeoutError(f"LLM call timed out after {timeout}s")
            logger.error(
                "[%s] TIMEOUT | attempt=%d/%d elapsed=%.1fs timeout=%.0fs %s",
                agent_name, attempt, max_retries, elapsed, timeout,
                " ".join(f"{k}={v}" for k, v in ctx.items() if k != "_emitter") if ctx else "",
            )
            # Emit agent_error
            await _emit_event(on_event, "agent_error", agent_name, ctx, {
                "error": f"Timeout after {timeout:.0f}s",
                "error_type": "timeout",
                "elapsed_ms": int(elapsed * 1000),
                "attempt": attempt,
            })

        except Exception as exc:
            elapsed = time.monotonic() - t0
            last_error = exc
            logger.error(
                "[%s] ERROR | attempt=%d/%d elapsed=%.1fs error=%s %s",
                agent_name, attempt, max_retries, elapsed, str(exc)[:300],
                " ".join(f"{k}={v}" for k, v in ctx.items() if k != "_emitter") if ctx else "",
            )
            # Emit agent_error
            await _emit_event(on_event, "agent_error", agent_name, ctx, {
                "error": str(exc)[:200],
                "error_type": type(exc).__name__,
                "elapsed_ms": int(elapsed * 1000),
                "attempt": attempt,
            })

        if attempt < max_retries:
            wait = retry_delay * attempt
            logger.info(
                "[%s] Retrying in %.1fs (attempt %d/%d) %s",
                agent_name, wait, attempt + 1, max_retries,
                " ".join(f"{k}={v}" for k, v in ctx.items() if k != "_emitter") if ctx else "",
            )
            await asyncio.sleep(wait)

    raise AgentResponseError(
        f"[{agent_name}] Failed after {max_retries} attempts: {last_error}"
    )
