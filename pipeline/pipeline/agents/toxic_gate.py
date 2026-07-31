"""Runtime toxic-content quarantine gate (design doc §7.4).

Reuses the EXISTING DeepEval ToxicityMetric via the judge-gate scoring
service (evals/scoring/judge_gate_service.py) over HTTP — no classifier is
reimplemented here. Checks the combined review text first (cheap, common
case); only on failure does it check title/abstract/each section separately
to name which field tripped, since a bare "toxic content detected" reason
gives a human reviewer nothing to act on when deciding whether a quarantined
job is a real problem or the false positive §7.4 explicitly worries about.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from pipeline.agents.review_text import build_review_text
from pipeline.config import settings

logger = logging.getLogger(__name__)


class ToxicGateResult(BaseModel):
    """Outcome of the toxic-content runtime gate."""

    verdict: Literal["pass", "quarantine"]
    reason: str | None = None
    score: float | None = None


async def check_toxicity(review: dict[str, Any]) -> ToxicGateResult:
    """Check the assembled review for toxic content, or pass through if disabled.

    The gate is opt-in via PIPELINE_TOXIC_GATE_URL (unset = disabled, same
    convention as PIPELINE_API_KEY/PIPELINE_JUDGE_GATE_URL). Once configured,
    a request failure is treated as a gate failure (quarantine) rather than a
    silent pass — matching §7.4's "quarantine, don't silently reject [or
    serve]" policy.
    """
    if not settings.toxic_gate_url:
        return ToxicGateResult(verdict="pass")

    try:
        async with httpx.AsyncClient(timeout=settings.toxic_gate_timeout) as client:
            combined = await _score_text(client, build_review_text(review))
    except httpx.HTTPError as exc:
        logger.error("Toxic gate unreachable: %s", exc, exc_info=True)
        return ToxicGateResult(
            verdict="quarantine", reason=f"toxic-gate service unreachable: {exc}",
        )

    if combined["passed"]:
        return ToxicGateResult(verdict="pass", score=combined["score"])

    try:
        async with httpx.AsyncClient(timeout=settings.toxic_gate_timeout) as client:
            failed_fields = await _find_failed_fields(client, review)
    except httpx.HTTPError as exc:
        logger.error("Toxic gate unreachable during decompose: %s", exc, exc_info=True)
        failed_fields = []

    reason = (
        f"toxic content detected in: {', '.join(failed_fields)}"
        if failed_fields
        else "toxic content detected"
    )
    return ToxicGateResult(verdict="quarantine", reason=reason, score=combined["score"])


async def _score_text(client: httpx.AsyncClient, text: str) -> dict[str, Any]:
    response = await client.post(f"{settings.toxic_gate_url}/score-toxicity", json={"text": text})
    response.raise_for_status()
    return response.json()


async def _find_failed_fields(client: httpx.AsyncClient, review: dict[str, Any]) -> list[str]:
    """Re-check title/abstract/each section individually to name the culprit(s)."""
    fields: list[tuple[str, str]] = [
        ("title", review.get("title", "")),
        ("abstract", review.get("abstract", "")),
    ]
    for section in review.get("sections", []):
        label = section.get("label") or section.get("theme_id", "section")
        fields.append((f"section '{label}'", section.get("content", "")))

    failed = []
    for name, text in fields:
        if not text:
            continue
        result = await _score_text(client, text)
        if not result["passed"]:
            failed.append(name)
    return failed
