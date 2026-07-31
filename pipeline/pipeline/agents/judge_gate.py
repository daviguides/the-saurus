"""Post-aggregation LLM-as-Judge runtime gate (design doc §8.2).

Scores the assembled review against the EXISTING GEval faithfulness/
citation-accuracy rubric by calling the judge-gate scoring service
(evals/scoring/judge_gate_service.py) over HTTP — no judge logic is
reimplemented here. See the task's research.md/plan.md for why this is an
HTTP call rather than a direct import.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from pipeline.config import settings

logger = logging.getLogger(__name__)


class JudgeGateResult(BaseModel):
    """Outcome of the post-aggregation judge gate."""

    verdict: Literal["pass", "quarantine"]
    reason: str | None = None
    scores: dict[str, float] = {}


async def score_review(
    review: dict[str, Any], claims: list[dict[str, Any]]
) -> JudgeGateResult:
    """Score the assembled review, or pass through if the gate is disabled.

    The gate is opt-in via PIPELINE_JUDGE_GATE_URL (unset = disabled, same
    convention as PIPELINE_API_KEY). Once configured, a request failure is
    treated as a gate failure (quarantine) rather than a silent pass —
    matching §7.4's "quarantine, don't silently [bypass]" policy.
    """
    if not settings.judge_gate_url:
        return JudgeGateResult(verdict="pass")

    payload = {
        "actual_output": _build_actual_output(review),
        "retrieval_context": [c.get("text", "") for c in claims],
        "expected_output": json.dumps(review),
    }

    try:
        async with httpx.AsyncClient(timeout=settings.judge_gate_timeout) as client:
            response = await client.post(
                f"{settings.judge_gate_url}/score-review", json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.error("Judge gate unreachable: %s", exc, exc_info=True)
        return JudgeGateResult(
            verdict="quarantine", reason=f"judge service unreachable: {exc}",
        )

    faithfulness = data["faithfulness"]
    citation_accuracy = data["citation_accuracy"]
    scores = {
        "faithfulness": faithfulness["score"],
        "citation_accuracy": citation_accuracy["score"],
    }

    if data["verdict"] == "pass":
        return JudgeGateResult(verdict="pass", scores=scores)

    failed = [
        name
        for name, result in (
            ("faithfulness", faithfulness),
            ("citation_accuracy", citation_accuracy),
        )
        if not result["passed"]
    ]
    reason = f"judge gate failed rubric item(s): {', '.join(failed)}"
    return JudgeGateResult(verdict="quarantine", reason=reason, scores=scores)


def _build_actual_output(review: dict[str, Any]) -> str:
    """Flatten title/abstract/sections into the text the judge model scores."""
    sections_text = "\n\n".join(
        f"## {s.get('label', '')}\n{s.get('content', '')}"
        for s in review.get("sections", [])
    )
    return f"# {review.get('title', '')}\n\n{review.get('abstract', '')}\n\n{sections_text}"
