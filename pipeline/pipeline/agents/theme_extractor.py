"""Theme extractor agent: extracts thematic groups from a single paper."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.prompts.theme_extractor import THEME_EXTRACTOR_PROMPT

# --- Pydantic output models ---


class ThemePosition(BaseModel):
    """A location in the paper where a theme appears."""

    page: int
    paragraph: int


class ExtractedTheme(BaseModel):
    """A single theme extracted from a paper."""

    name: str
    description: str
    positions: list[ThemePosition] = Field(min_length=1)


class ThemeExtractionResult(BaseModel):
    """Structured output from the theme extractor LLM."""

    themes: list[ExtractedTheme] = Field(min_length=1)


# --- Agent ---


class ThemeExtractorAgent:
    """Extracts thematic groups from a single paper's annotated markdown.

    Wraps an Agno agent internally but satisfies the pipeline Agent protocol.
    """

    def __init__(self) -> None:
        self._agent = AgnoAgent(
            name="ThemeExtractor",
            model=create_model(),
            instructions=THEME_EXTRACTOR_PROMPT,
            structured_outputs=True,
        )

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        paper_id = input["paper_id"]
        content = input["content"]

        result = await self._agent.arun(
            content,
            output_schema=ThemeExtractionResult,
        )

        extraction: ThemeExtractionResult = result.content
        return {
            "themes": [
                {
                    "id": str(uuid4()),
                    "name": theme.name,
                    "description": theme.description,
                    "paper_id": paper_id,
                    "positions": [p.model_dump() for p in theme.positions],
                }
                for theme in extraction.themes
            ]
        }
