"""Tests for claim extractor: Pydantic models, agent protocol, agent run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, patch

from tests.conftest import mock_streaming_arun

import pytest

from pipeline.agents.protocol import Agent
from pipeline.agents.claim_extractor import (
    ClaimExtractionResult,
    ClaimExtractorAgent,
    ClaimPosition,
    ExtractedClaim,
)

# --- Pydantic model tests ---


class TestPydanticModels:
    def test_claim_position_valid(self) -> None:
        pos = ClaimPosition(page=5, paragraph=3)
        assert pos.page == 5
        assert pos.paragraph == 3

    def test_extracted_claim_valid(self) -> None:
        claim = ExtractedClaim(
            theme_name="Viral Vectors",
            text="AAV9 showed 80% transduction efficiency.",
            position=ClaimPosition(page=3, paragraph=2),
            deep="[p.3,§2] In our experiments, AAV9 showed 80% transduction efficiency in murine models, significantly higher than AAV2.",
            summary="AAV9 achieves 80% transduction efficiency in mice.",
        )
        assert claim.theme_name == "Viral Vectors"
        assert claim.position.page == 3

    def test_extraction_result_requires_claims(self) -> None:
        with pytest.raises(Exception):
            ClaimExtractionResult(claims=[])

    def test_extraction_result_valid(self) -> None:
        result = ClaimExtractionResult(
            claims=[
                ExtractedClaim(
                    theme_name="CRISPR",
                    text="Guide RNA specificity was 99.2%.",
                    position=ClaimPosition(page=1, paragraph=1),
                    deep="Full paragraph context here.",
                    summary="Guide RNA achieved 99.2% specificity.",
                ),
            ]
        )
        assert len(result.claims) == 1


# --- Agent protocol tests ---


class TestAgentProtocol:
    def test_satisfies_protocol(self) -> None:
        with patch("pipeline.agents.claim_extractor.AgnoAgent"):
            agent = ClaimExtractorAgent()
        assert isinstance(agent, Agent)


# --- Agent run tests ---


@dataclass
class FakeRunOutput:
    content: Any


class TestClaimExtractorAgentRun:
    @pytest.fixture
    def input_themes(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "theme-uuid-1",
                "name": "Viral Vectors",
                "description": "AAV-based delivery systems.",
                "paper_id": "paper-123",
                "positions": [{"page": 3, "paragraph": 2}],
            },
            {
                "id": "theme-uuid-2",
                "name": "Immunogenicity",
                "description": "Immune responses.",
                "paper_id": "paper-123",
                "positions": [{"page": 5, "paragraph": 4}],
            },
        ]

    @pytest.fixture
    def mock_extraction(self) -> ClaimExtractionResult:
        return ClaimExtractionResult(
            claims=[
                ExtractedClaim(
                    theme_name="Viral Vectors",
                    text="AAV9 showed 80% transduction efficiency.",
                    position=ClaimPosition(page=3, paragraph=2),
                    deep="[p.3,§2] In our experiments, AAV9 showed 80% transduction efficiency in murine models.",
                    summary="AAV9 achieves 80% transduction efficiency in mice.",
                ),
                ExtractedClaim(
                    theme_name="Immunogenicity",
                    text="Anti-AAV antibodies were detected in 30% of subjects.",
                    position=ClaimPosition(page=5, paragraph=4),
                    deep="[p.5,§4] Anti-AAV antibodies were detected in 30% of subjects after the first dose.",
                    summary="30% of subjects developed anti-AAV antibodies.",
                ),
            ]
        )

    async def test_run_returns_claims_with_ids(
        self,
        mock_extraction: ClaimExtractionResult,
        input_themes: list[dict[str, Any]],
    ) -> None:
        fake_output = FakeRunOutput(content=mock_extraction)

        with patch("pipeline.agents.claim_extractor.AgnoAgent"):
            agent = ClaimExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = mock_streaming_arun(fake_output)

        result = await agent.run({
            "paper_id": "paper-123",
            "title": "Test Paper",
            "content": "[p.3,§2] Some annotated markdown.",
            "themes": input_themes,
        })

        claims = result["claims"]
        assert len(claims) == 2

        c = claims[0]
        assert c["theme_name"] == "Viral Vectors"
        assert c["theme_id"] == "theme-uuid-1"
        assert c["text"] == "AAV9 showed 80% transduction efficiency."
        assert c["page"] == 3
        assert c["paragraph"] == 2
        assert "deep" in c
        assert "summary" in c
        assert "id" in c
        assert len(c["id"]) > 0

        # Check source dict for downstream compatibility
        assert c["source"]["paper_id"] == "paper-123"
        assert c["source"]["page"] == 3
        assert c["source"]["paragraph"] == 2

    async def test_run_resolves_theme_ids(
        self,
        mock_extraction: ClaimExtractionResult,
        input_themes: list[dict[str, Any]],
    ) -> None:
        fake_output = FakeRunOutput(content=mock_extraction)

        with patch("pipeline.agents.claim_extractor.AgnoAgent"):
            agent = ClaimExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = mock_streaming_arun(fake_output)

        result = await agent.run({
            "paper_id": "paper-123",
            "title": "Test Paper",
            "content": "text",
            "themes": input_themes,
        })

        claims = result["claims"]
        assert claims[0]["theme_id"] == "theme-uuid-1"
        assert claims[1]["theme_id"] == "theme-uuid-2"

    async def test_run_case_insensitive_theme_matching(
        self,
        input_themes: list[dict[str, Any]],
    ) -> None:
        extraction = ClaimExtractionResult(
            claims=[
                ExtractedClaim(
                    theme_name="viral vectors",  # lowercase
                    text="A claim.",
                    position=ClaimPosition(page=1, paragraph=1),
                    deep="Context.",
                    summary="Summary.",
                ),
            ]
        )
        fake_output = FakeRunOutput(content=extraction)

        with patch("pipeline.agents.claim_extractor.AgnoAgent"):
            agent = ClaimExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = mock_streaming_arun(fake_output)

        result = await agent.run({
            "paper_id": "p1",
            "title": "T",
            "content": "text",
            "themes": input_themes,
        })

        assert result["claims"][0]["theme_id"] == "theme-uuid-1"

    async def test_run_generates_unique_ids(
        self,
        mock_extraction: ClaimExtractionResult,
        input_themes: list[dict[str, Any]],
    ) -> None:
        fake_output = FakeRunOutput(content=mock_extraction)

        with patch("pipeline.agents.claim_extractor.AgnoAgent"):
            agent = ClaimExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = mock_streaming_arun(fake_output)

        result = await agent.run({
            "paper_id": "p1",
            "title": "T",
            "content": "text",
            "themes": input_themes,
        })

        ids = [c["id"] for c in result["claims"]]
        assert len(set(ids)) == len(ids)

    async def test_run_passes_themes_in_message(
        self,
        mock_extraction: ClaimExtractionResult,
        input_themes: list[dict[str, Any]],
    ) -> None:
        fake_output = FakeRunOutput(content=mock_extraction)

        with patch("pipeline.agents.claim_extractor.AgnoAgent"):
            agent = ClaimExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = mock_streaming_arun(fake_output)

        await agent.run({
            "paper_id": "p1",
            "title": "T",
            "content": "the paper content",
            "themes": input_themes,
        })

        call_args = agent._agent.arun.call_args
        message = call_args[0][0]
        assert "Viral Vectors" in message
        assert "Immunogenicity" in message
        assert "the paper content" in message

    async def test_run_without_themes(self) -> None:
        extraction = ClaimExtractionResult(
            claims=[
                ExtractedClaim(
                    theme_name="Unknown Theme",
                    text="A claim.",
                    position=ClaimPosition(page=1, paragraph=1),
                    deep="Context.",
                    summary="Summary.",
                ),
            ]
        )
        fake_output = FakeRunOutput(content=extraction)

        with patch("pipeline.agents.claim_extractor.AgnoAgent"):
            agent = ClaimExtractorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = mock_streaming_arun(fake_output)

        result = await agent.run({
            "paper_id": "p1",
            "title": "T",
            "content": "text",
        })

        # Should still work — theme_id gets a fallback UUID
        claims = result["claims"]
        assert len(claims) == 1
        assert len(claims[0]["theme_id"]) > 0
        assert claims[0]["source"]["paper_id"] == "p1"
