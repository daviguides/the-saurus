"""Theme reviewer agent: synthesizes claims across papers for batches of themes."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.parsing import run_agent_with_retry
from pipeline.agents.prompts.theme_reviewer import THEME_REVIEWER_PROMPT

logger = logging.getLogger(__name__)

# Themes per LLM call — balances quality vs call count
BATCH_SIZE = 5

# --- Pydantic output models ---


class ReviewedClaim(BaseModel):
    """A claim referenced in the review, with its source."""

    claim_id: str
    paper_id: str
    summary: str


class SingleThemeReview(BaseModel):
    """Review output for one theme within a batch."""

    theme_name: str
    synthesis: str = Field(min_length=1)
    consensus: list[str] = Field(min_length=1)
    disagreements: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    key_claims: list[ReviewedClaim] = Field(default_factory=list)


class BatchThemeReviewResult(BaseModel):
    """Structured output: reviews for multiple themes in one call."""

    reviews: list[SingleThemeReview] = Field(min_length=1)


# --- Agent ---


class ThemeReviewerAgent:
    """Synthesizes claims across papers for canonical themes.

    Processes themes in batches (default 5 per call) to balance
    LLM attention quality vs call count.
    """

    def __init__(self, batch_size: int = BATCH_SIZE) -> None:
        self._agent = AgnoAgent(
            name="ThemeReviewer",
            model=create_model(),
            instructions=THEME_REVIEWER_PROMPT,
            markdown=True,
        )
        self._batch_size = batch_size

    async def run_batch(
        self,
        themes: list[dict[str, Any]],
        all_claims: list[dict[str, Any]],
        *,
        on_event: Callable[[Any], Awaitable[None]] | None = None,
    ) -> list[dict[str, Any]]:
        """Process all themes in batches, return list of review dicts."""
        # Build claim index by theme_id
        claims_by_theme_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for claim in all_claims:
            tid = claim.get("theme_id", "")
            claims_by_theme_id[tid].append(claim)

        # Chunk themes into batches
        batches = [
            themes[i:i + self._batch_size]
            for i in range(0, len(themes), self._batch_size)
        ]

        logger.info(
            "ThemeReviewer: %d themes in %d batches (size %d)",
            len(themes), len(batches), self._batch_size,
        )

        all_reviews: list[dict[str, Any]] = []

        for batch_idx, batch in enumerate(batches, 1):
            # Collect relevant claims for this batch
            batch_claims: dict[str, list[dict[str, Any]]] = {}
            for theme in batch:
                source_ids = set(theme.get("source_theme_ids", []))
                if source_ids:
                    relevant = [c for c in all_claims if c.get("theme_id") in source_ids]
                else:
                    relevant = claims_by_theme_id.get(theme["id"], [])
                batch_claims[theme["id"]] = relevant

            message = _build_batch_message(batch, batch_claims)

            result = await run_agent_with_retry(
                self._agent, message, BatchThemeReviewResult,
                context={
                    "stage": "theme_review",
                    "batch": f"{batch_idx}/{len(batches)}",
                    "themes_in_batch": len(batch),
                    "total_claims": sum(len(v) for v in batch_claims.values()),
                },
                on_event=on_event,
            )

            # Map results back to theme IDs
            theme_name_to_id = {
                t.get("name", "").lower().strip(): t["id"] for t in batch
            }
            theme_name_to_meta = {
                t.get("name", "").lower().strip(): t for t in batch
            }

            for review in result.reviews:
                name_key = review.theme_name.lower().strip()
                theme_id = theme_name_to_id.get(name_key, "")
                theme_meta = theme_name_to_meta.get(name_key, {})

                # Validate claim IDs
                valid_ids = set()
                for claims_list in batch_claims.values():
                    for c in claims_list:
                        valid_ids.add(c.get("id", ""))
                validated_claims = [
                    kc for kc in review.key_claims if kc.claim_id in valid_ids
                ]

                all_reviews.append({
                    "theme_id": theme_id or review.theme_name,
                    "label": theme_meta.get("name", review.theme_name),
                    "review": review.synthesis,
                    "consensus": review.consensus,
                    "disagreements": review.disagreements,
                    "gaps": review.gaps,
                    "claim_ids": [kc.claim_id for kc in validated_claims],
                    "key_claims": [kc.model_dump() for kc in validated_claims],
                })

        return all_reviews


def _build_batch_message(
    themes: list[dict[str, Any]],
    claims_per_theme: dict[str, list[dict[str, Any]]],
) -> str:
    """Build LLM message with multiple themes and their claims."""
    lines: list[str] = []
    lines.append(f"Analyze the following {len(themes)} themes:\n")

    for i, theme in enumerate(themes, 1):
        name = theme.get("name", theme.get("label", "Unknown"))
        desc = theme.get("description", "")
        aliases = ", ".join(theme.get("aliases", []))
        theme_id = theme["id"]

        lines.append(f"{'='*60}")
        lines.append(f"THEME {i}: {name}")
        lines.append(f"DESCRIPTION: {desc}")
        if aliases:
            lines.append(f"ALIASES: {aliases}")

        # Group claims by paper
        claims = claims_per_theme.get(theme_id, [])
        by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for claim in claims:
            pid = claim.get("source", {}).get("paper_id", "unknown")
            by_paper[pid].append(claim)

        lines.append(f"PAPERS: {len(by_paper)} paper(s), {len(claims)} claims")
        lines.append("")

        for pid, paper_claims in by_paper.items():
            lines.append(f"  Paper: {pid}")
            for claim in paper_claims:
                cid = claim.get("id", "?")
                summary = claim.get("summary", claim.get("text", ""))
                page = claim.get("page", claim.get("source", {}).get("page", "?"))
                para = claim.get("paragraph", claim.get("source", {}).get("paragraph", "?"))
                deep = claim.get("deep", "")
                lines.append(f"  [{cid}] {summary} (p.{page},§{para})")
                if deep:
                    lines.append(f"      Context: {deep[:300]}")
            lines.append("")

        lines.append("")

    return "\n".join(lines)
