"""Parse LLM responses into Pydantic models with retry logic and observability.

Calls the Gemini API directly for finer control over response handling,
retries, and structured output parsing. Agno Agent objects carry name +
instructions while the LLM call goes through google.genai.Client.
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

LLM_TIMEOUT = 300.0  # seconds — large papers can take 190s+


class AgentResponseError(Exception):
    """Raised when the LLM response cannot be parsed after retries."""


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


def parse_agent_response(raw: object, model_class: type[T]) -> T:
    """Parse an LLM response into the expected Pydantic model."""
    if isinstance(raw, model_class):
        return raw

    if raw is None:
        raise AgentResponseError(f"LLM returned None, expected {model_class.__name__}")

    if isinstance(raw, str):
        cleaned = raw.strip()
        if not cleaned:
            raise AgentResponseError(
                f"LLM returned empty string, expected {model_class.__name__}"
            )
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if json_match:
            cleaned = json_match.group(1).strip()
        return model_class.model_validate_json(cleaned)

    if isinstance(raw, dict):
        return model_class.model_validate(raw)

    return model_class.model_validate_json(str(raw))


async def _emit_event(
    ctx: dict[str, Any],
    event_type: str,
    agent_name: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a synthetic agent event through the pipeline EventEmitter."""
    emitter = ctx.get("_emitter")
    if emitter is None:
        return
    from pipeline.agents.step_messages import get_step_message, get_technical_message
    from pipeline.core.events import EventType

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

    event_type_enum = getattr(EventType, event_type.upper(), event_type)
    try:
        await emitter.emit(event_type_enum, payload)
    except Exception:
        logger.warning("[%s] Failed to emit %s event", agent_name, event_type)


def _ctx_str(ctx: dict[str, Any]) -> str:
    """Format context dict for log messages, excluding internal keys."""
    return " ".join(f"{k}={v}" for k, v in ctx.items() if not k.startswith("_"))


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
    """Call Gemini API directly with retry logic, timeout, and Pydantic parsing.

    Uses the agent's name and instructions for prompt composition while calling
    the Gemini API directly for full control over response handling and parsing.
    """
    from pipeline.agents.models import llm_semaphore
    from pipeline.config import settings
    import google.genai as genai

    if max_retries is None:
        max_retries = settings.llm_max_retries
    if retry_delay is None:
        retry_delay = settings.llm_retry_delay

    ctx = context or {}

    job_dir: Path | None = None
    if ctx.get("job_dir"):
        job_dir = Path(ctx["job_dir"]) / "raw"

    agent_name = getattr(agent, "name", agent.__class__.__name__)
    instructions = getattr(agent, "instructions", "") or ""
    if not instructions:
        inner = getattr(agent, "_agent", None)
        if inner:
            instructions = getattr(inner, "instructions", "") or ""

    model_id = settings.llm_model_id
    msg_chars = len(message)
    msg_tokens = estimate_tokens(message)

    logger.info(
        "[%s] Starting | input_chars=%d input_tokens=~%d schema=%s model=%s %s",
        agent_name, msg_chars, msg_tokens, output_schema.__name__, model_id, _ctx_str(ctx),
    )

    client = genai.Client(api_key=settings.llm_api_key)
    full_prompt = f"{instructions}\n\n{message}"

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        t0 = time.monotonic()

        await _emit_event(ctx, "agent_started", agent_name, {
            "model": model_id,
            "input_tokens": msg_tokens,
            "attempt": attempt,
        })

        try:
            async with llm_semaphore:
                logger.info(
                    "[%s] Acquired semaphore (attempt %d/%d) %s",
                    agent_name, attempt, max_retries, _ctx_str(ctx),
                )
                async with asyncio.timeout(timeout):
                    result = await asyncio.to_thread(
                        client.models.generate_content,
                        model=model_id,
                        contents=full_prompt,
                    )

            elapsed = time.monotonic() - t0
            elapsed_ms = int(elapsed * 1000)

            # Extract response
            raw: str | None = None
            finish_reason = None
            safety_ratings = None

            if result.candidates:
                candidate = result.candidates[0]
                finish_reason = candidate.finish_reason
                safety_ratings = candidate.safety_ratings
                if candidate.content and candidate.content.parts:
                    raw = candidate.content.parts[0].text

            raw_len = len(raw) if raw else 0
            logger.info(
                "[%s] Gemini responded | attempt=%d/%d elapsed=%.1fs len=%d finish=%s %s",
                agent_name, attempt, max_retries, elapsed, raw_len, finish_reason, _ctx_str(ctx),
            )

            if not raw:
                logger.warning(
                    "[%s] Empty response | finish=%s safety=%s %s",
                    agent_name, finish_reason, safety_ratings, _ctx_str(ctx),
                )
                raise AgentResponseError(
                    f"Gemini returned empty response (finish={finish_reason}, safety={safety_ratings})"
                )

            # Save raw response for debugging
            if job_dir:
                try:
                    job_dir.mkdir(parents=True, exist_ok=True)
                    paper_id = ctx.get("paper_id", "unknown")
                    stage = ctx.get("stage", agent_name)
                    filename = f"{paper_id}_{stage}_attempt{attempt}.txt"
                    (job_dir / filename).write_text(raw[:500_000])
                except Exception:
                    pass

            parsed = parse_agent_response(raw, output_schema)
            logger.info(
                "[%s] Parsed OK | attempt=%d/%d elapsed=%.1fs %s",
                agent_name, attempt, max_retries, elapsed, _ctx_str(ctx),
            )

            await _emit_event(ctx, "agent_completed", agent_name, {
                "elapsed_ms": elapsed_ms,
                "response_len": raw_len,
            })

            return parsed

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - t0
            last_error = TimeoutError(f"LLM call timed out after {timeout}s")
            logger.error(
                "[%s] TIMEOUT | attempt=%d/%d elapsed=%.1fs timeout=%.0fs %s",
                agent_name, attempt, max_retries, elapsed, timeout, _ctx_str(ctx),
            )
            await _emit_event(ctx, "agent_error", agent_name, {
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
                agent_name, attempt, max_retries, elapsed, str(exc)[:300], _ctx_str(ctx),
            )
            await _emit_event(ctx, "agent_error", agent_name, {
                "error": str(exc)[:200],
                "error_type": type(exc).__name__,
                "elapsed_ms": int(elapsed * 1000),
                "attempt": attempt,
            })

        if attempt < max_retries:
            wait = retry_delay * attempt
            logger.info(
                "[%s] Retrying in %.1fs (attempt %d/%d) %s",
                agent_name, wait, attempt + 1, max_retries, _ctx_str(ctx),
            )
            await asyncio.sleep(wait)

    raise AgentResponseError(
        f"[{agent_name}] Failed after {max_retries} attempts: {last_error}"
    )
