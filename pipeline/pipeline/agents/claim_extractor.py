"""Claim extractor agent: extracts claims per theme from a single paper."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.prompts.claim_extractor import CLAIM_EXTRACTOR_PROMPT

# --- Pydantic output models ---


class ClaimPosition(BaseModel):
    """A location in the paper where a claim appears."""

    page: int
    paragraph: int


class ExtractedClaim(BaseModel):
    """A single claim extracted from a paper."""

    theme_name: str
    text: str
    position: ClaimPosition
    deep: str
    summary: str


class ClaimExtractionResult(BaseModel):
    """Structured output from the claim extractor LLM."""

    claims: list[ExtractedClaim] = Field(min_length=1)


# --- Agent ---


class ClaimExtractorAgent:
    """Extracts claims per theme from a single paper's annotated markdown.

    Wraps an Agno agent internally but satisfies the pipeline Agent protocol.
    """

    def __init__(self) -> None:
        self._agent = AgnoAgent(
            name="ClaimExtractor",
            model=create_model(),
            instructions=CLAIM_EXTRACTOR_PROMPT,
            structured_outputs=True,
        )

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        paper_id = input["paper_id"]
        content = input["content"]
        themes = input.get("themes", [])

        # Build theme context for prompt
        theme_lines = "\n".join(
            f"- {t['name']}: {t.get('description', '')}" for t in themes
        )

        # Build theme ID lookup (case-insensitive)
        theme_lookup = {t["name"].lower().strip(): t["id"] for t in themes}

        message = f"{theme_lines}\n\n{content}"

        result = await self._agent.arun(
            message,
            output_schema=ClaimExtractionResult,
        )

        extraction: ClaimExtractionResult = result.content
        return {
            "claims": [
                {
                    "id": str(uuid4()),
                    "theme_id": theme_lookup.get(
                        claim.theme_name.lower().strip(), str(uuid4())
                    ),
                    "theme_name": claim.theme_name,
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
                }
                for claim in extraction.claims
            ]
        }
