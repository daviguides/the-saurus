"""Tests for theme extractor: annotated markdown, Pydantic models, agent protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.agents.protocol import Agent
from pipeline.agents.theme_extractor import (
    ExtractedTheme,
    ThemeExtractionResult,
    ThemeExtractorAgent,
    ThemePosition,
)
from pipeline.ingestion.models import IngestedPaper, Paragraph

# --- to_annotated_markdown tests ---


class TestAnnotatedMarkdown:
    def test_body_paragraph_has_position_tag(self) -> None:
        paper = IngestedPaper(
            title="Test",
            paragraphs=[Paragraph(page=3, index=2, text="Some body text.")],
        )
        md = paper.to_annotated_markdown()
        assert "[p.3,§2] Some body text." in md

    def test_heading_has_position_tag(self) -> None:
        paper = IngestedPaper(
            title="Test",
            paragraphs=[
                Paragraph(page=1, index=1, text="Introduction", is_heading=True, heading_level=2),
            ],
        )
        md = paper.to_annotated_markdown()
        assert "## [p.1,§1] Introduction" in md

    def test_title_heading(self) -> None:
        paper = IngestedPaper(
            title="My Paper",
            paragraphs=[
                Paragraph(page=1, index=1, text="My Paper", is_heading=True, heading_level=1),
            ],
        )
        md = paper.to_annotated_markdown()
        assert "# [p.1,§1] My Paper" in md

    def test_multiple_paragraphs_all_tagged(self) -> None:
        paper = IngestedPaper(
            title="Test",
            paragraphs=[
                Paragraph(page=1, index=1, text="Title", is_heading=True, heading_level=1),
                Paragraph(page=1, index=2, text="First para."),
                Paragraph(page=2, index=1, text="Section 2", is_heading=True, heading_level=2),
                Paragraph(page=2, index=2, text="Second page text."),
            ],
        )
        md = paper.to_annotated_markdown()
        assert "[p.1,§1]" in md
        assert "[p.1,§2]" in md
        assert "[p.2,§1]" in md
        assert "[p.2,§2]" in md

    def test_blank_lines_between_paragraphs(self) -> None:
        paper = IngestedPaper(
            title="Test",
            paragraphs=[
                Paragraph(page=1, index=1, text="Para one."),
                Paragraph(page=1, index=2, text="Para two."),
            ],
        )
        md = paper.to_annotated_markdown()
        lines = md.split("\n")
        non_empty = [i for i, line in enumerate(lines) if line.strip()]
        for i in range(len(non_empty) - 1):
            assert non_empty[i + 1] - non_empty[i] >= 2

    def test_original_to_markdown_unchanged(self) -> None:
        paper = IngestedPaper(
            title="Test",
            paragraphs=[Paragraph(page=1, index=1, text="Body text.")],
        )
        md = paper.to_markdown()
        assert "[p." not in md
        assert "Body text." in md


# --- Pydantic model tests ---


class TestPydanticModels:
    def test_theme_position_valid(self) -> None:
        pos = ThemePosition(page=5, paragraph=3)
        assert pos.page == 5
        assert pos.paragraph == 3

    def test_extracted_theme_requires_positions(self) -> None:
        with pytest.raises(Exception):
            ExtractedTheme(name="Test", description="Desc", positions=[])

    def test_extracted_theme_valid(self) -> None:
        theme = ExtractedTheme(
            name="Gene Therapy",
            description="Approaches to genetic modification.",
            positions=[ThemePosition(page=1, paragraph=2)],
        )
        assert theme.name == "Gene Therapy"
        assert len(theme.positions) == 1

    def test_extraction_result_requires_themes(self) -> None:
        with pytest.raises(Exception):
            ThemeExtractionResult(themes=[])

    def test_extraction_result_valid(self) -> None:
        result = ThemeExtractionResult(
            themes=[
                ExtractedTheme(
                    name="CRISPR",
                    description="Gene editing.",
                    positions=[ThemePosition(page=1, paragraph=1)],
                ),
            ]
        )
        assert len(result.themes) == 1


# --- Agent protocol tests ---


class TestAgentProtocol:
    def test_satisfies_protocol(self) -> None:
        with patch("pipeline.agents.theme_extractor.AgnoAgent"):
            agent = ThemeExtractorAgent()
        assert isinstance(agent, Agent)


# --- Agent run tests ---


@dataclass
class FakeRunOutput:
    content: Any


class TestThemeExtractorAgentRun:
    @pytest.fixture
    def mock_extraction(self) -> ThemeExtractionResult:
        return ThemeExtractionResult(
            themes=[
                ExtractedTheme(
                    name="Viral Vectors",
                    description="AAV-based delivery systems for gene therapy.",
                    positions=[
                        ThemePosition(page=3, paragraph=2),
                        ThemePosition(page=7, paragraph=1),
                    ],
                ),
                ExtractedTheme(
                    name="Immunogenicity",
                    description="Immune responses to viral vectors.",
                    positions=[ThemePosition(page=5, paragraph=4)],
                ),
            ]
        )

    async def test_run_returns_themes_with_ids(
        self, mock_extraction: ThemeExtractionResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_extraction)

        with patch("pipeline.agents.theme_extractor.AgnoAgent"):
            agent = ThemeExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({
            "paper_id": "paper-123",
            "title": "Test Paper",
            "content": "[p.1,§1] Some annotated markdown.",
        })

        themes = result["themes"]
        assert len(themes) == 2

        # Check first theme structure
        t = themes[0]
        assert t["name"] == "Viral Vectors"
        assert t["description"] == "AAV-based delivery systems for gene therapy."
        assert t["paper_id"] == "paper-123"
        assert "id" in t
        assert len(t["id"]) > 0
        assert len(t["positions"]) == 2
        assert t["positions"][0] == {"page": 3, "paragraph": 2}

        # Check second theme
        assert themes[1]["name"] == "Immunogenicity"
        assert len(themes[1]["positions"]) == 1

    async def test_run_generates_unique_ids(
        self, mock_extraction: ThemeExtractionResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_extraction)

        with patch("pipeline.agents.theme_extractor.AgnoAgent"):
            agent = ThemeExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({
            "paper_id": "p1",
            "title": "T",
            "content": "text",
        })

        ids = [t["id"] for t in result["themes"]]
        assert len(set(ids)) == len(ids)  # all unique

    async def test_passes_content_to_agno(
        self, mock_extraction: ThemeExtractionResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_extraction)

        with patch("pipeline.agents.theme_extractor.AgnoAgent"):
            agent = ThemeExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        await agent.run({
            "paper_id": "p1",
            "title": "T",
            "content": "the paper content",
        })

        agent._agent.arun.assert_called_once_with(
            "the paper content",
            output_schema=ThemeExtractionResult,
        )
