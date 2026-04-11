"""Theme reviewer agent: synthesizes claims across papers for a single theme."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.parsing import run_agent_with_retry
from pipeline.agents.prompts.theme_reviewer import THEME_REVIEWER_PROMPT

# --- Pydantic output models ---


class ReviewedClaim(BaseModel):
    """A claim referenced in the review, with its source."""

    claim_id: str
    paper_id: str
    summary: str


class ThemeReviewResult(BaseModel):
    """Structured output from the theme reviewer LLM."""

    synthesis: str = Field(min_length=1)
    consensus: list[str] = Field(min_length=1)
    disagreements: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    key_claims: list[ReviewedClaim] = Field(default_factory=list)


# --- Agent ---


class ThemeReviewerAgent:
    """Synthesizes claims across papers for a single canonical theme.

    Wraps an Agno agent internally but satisfies the pipeline Agent protocol.
    """

    def __init__(self) -> None:
        self._agent = AgnoAgent(
            name="ThemeReviewer",
            model=create_model(),
            instructions=THEME_REVIEWER_PROMPT,
            structured_outputs=True,
        )

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        theme: dict[str, Any] = input["theme"]
        claims: list[dict[str, Any]] = input.get("claims", [])

        # Filter claims to only those matching this canonical theme
        source_theme_ids = set(theme.get("source_theme_ids", []))
        if source_theme_ids:
            relevant_claims = [
                c for c in claims if c.get("theme_id") in source_theme_ids
            ]
        else:
            relevant_claims = claims

        # Build message for LLM
        message = _build_message(theme, relevant_claims)

        review = await run_agent_with_retry(
            self._agent, message, ThemeReviewResult,
            context={"stage": "theme_review", "theme": theme.get("name", "?"), "claim_count": len(relevant_claims)},
        )

        # Validate claim IDs — only keep those present in input
        valid_ids = {c["id"] for c in relevant_claims}
        validated_claims = [
            kc for kc in review.key_claims if kc.claim_id in valid_ids
        ]

        return {
            "theme_id": theme["id"],
            "label": theme.get("label", theme.get("name", "")),
            "review": review.synthesis,
            "consensus": review.consensus,
            "disagreements": review.disagreements,
            "gaps": review.gaps,
            "claim_ids": [kc.claim_id for kc in validated_claims],
            "key_claims": [kc.model_dump() for kc in validated_claims],
        }


def _build_message(
    theme: dict[str, Any], claims: list[dict[str, Any]]
) -> str:
    """Build the LLM message with theme context and claims grouped by paper."""
    aliases = ", ".join(theme.get("aliases", []))
    lines = [
        f"THEME: {theme.get('name', theme.get('label', 'Unknown'))}",
        f"DESCRIPTION: {theme.get('description', '')}",
        f"ALIASES: {aliases}" if aliases else "",
    ]

    # Group claims by paper
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        pid = claim.get("source", {}).get("paper_id", "unknown")
        by_paper[pid].append(claim)

    paper_count = len(by_paper)
    lines.append(f"PAPERS: {paper_count} paper(s) contribute to this theme")
    lines.append("")
    lines.append("--- CLAIMS BY PAPER ---")

    for pid, paper_claims in by_paper.items():
        lines.append("")
        lines.append(f"Paper: {pid}")
        for claim in paper_claims:
            cid = claim.get("id", "?")
            summary = claim.get("summary", claim.get("text", ""))
            page = claim.get("page", claim.get("source", {}).get("page", "?"))
            para = claim.get("paragraph", claim.get("source", {}).get("paragraph", "?"))
            deep = claim.get("deep", "")
            lines.append(f"[{cid}] {summary} (p.{page},§{para})")
            if deep:
                lines.append(f"    Context: {deep}")

    return "\n".join(lines)
