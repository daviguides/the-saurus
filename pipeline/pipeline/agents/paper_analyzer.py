"""Paper analyzer agent: extracts themes AND claims in a single pass."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.parsing import run_agent_with_retry
from pipeline.agents.prompts.paper_analyzer import PAPER_ANALYZER_PROMPT

# --- Pydantic output models ---


class ClaimPosition(BaseModel):
    """A location in the paper where a claim appears."""

    page: int
    paragraph: int


class ExtractedClaim(BaseModel):
    """A single claim extracted from a paper."""

    text: str
    position: ClaimPosition
    deep: str
    summary: str


class ThemeWithClaims(BaseModel):
    """A theme with its associated claims — extracted together in one pass."""

    name: str
    description: str
    positions: list[ClaimPosition] = Field(min_length=1)
    claims: list[ExtractedClaim] = Field(min_length=1)


class PaperAnalysisResult(BaseModel):
    """Structured output: themes + claims extracted from a single paper."""

    themes: list[ThemeWithClaims] = Field(min_length=1)


# --- Agent ---


class PaperAnalyzerAgent:
    """Extracts themes and claims from a single paper in one LLM pass.

    The LLM reads the paper once and produces themes with their claims
    co-located, avoiding redundant re-reading of the paper.
    """

    def __init__(self) -> None:
        from pipeline.config import settings

        self._agent = AgnoAgent(
            name="PaperAnalyzer",
            model=create_model(),
            instructions=PAPER_ANALYZER_PROMPT,
            output_schema=PaperAnalysisResult,
            structured_outputs=True,
            debug_mode=settings.llm_debug_mode,
        )

    async def run(
        self,
        data: dict[str, Any],
        *,
        on_event: Callable[[Any], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        paper_id = data["paper_id"]
        content = data["content"]

        analysis = await run_agent_with_retry(
            self._agent, content, PaperAnalysisResult,
            context={
                "paper_id": paper_id,
                "paper_title": data.get("title", ""),
                "stage": "paper_analysis",
            },
            on_event=on_event,
        )

        # Split into separate themes and claims outputs
        # (maintains compatibility with downstream stages)
        themes_out = []
        claims_out = []

        for theme in analysis.themes:
            theme_id = str(uuid4())
            themes_out.append({
                "id": theme_id,
                "name": theme.name,
                "description": theme.description,
                "paper_id": paper_id,
                "positions": [p.model_dump() for p in theme.positions],
            })

            for claim in theme.claims:
                claims_out.append({
                    "id": str(uuid4()),
                    "theme_id": theme_id,
                    "theme_name": theme.name,
                    "text": claim.text,
                    "page": claim.position.page,
                    "paragraph": claim.position.paragraph,
                    "deep": claim.deep,
                    "summary": claim.summary,
                    "source": {
                        "paper_id": paper_id,
                        "page": claim.position.page,
                        "paragraph": claim.position.paragraph,
                    },
                })

        return {
            "themes": themes_out,
            "claims": claims_out,
        }
