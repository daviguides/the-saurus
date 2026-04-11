"""Tests for theme reviewer: Pydantic models, agent protocol, agent run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.agents.protocol import Agent
from pipeline.agents.theme_reviewer import (
    ReviewedClaim,
    ThemeReviewerAgent,
    ThemeReviewResult,
    _build_message,
)

# --- Pydantic model tests ---


class TestPydanticModels:
    def test_reviewed_claim_valid(self) -> None:
        claim = ReviewedClaim(
            claim_id="c1",
            paper_id="p1",
            summary="AAV9 achieves 80% transduction.",
        )
        assert claim.claim_id == "c1"
        assert claim.paper_id == "p1"

    def test_theme_review_result_valid(self) -> None:
        result = ThemeReviewResult(
            synthesis="Theme X is well studied across three papers.",
            consensus=["Papers agree on mechanism A."],
            disagreements=["Paper 1 and 2 differ on dosage."],
            gaps=["No study addresses long-term effects."],
            key_claims=[
                ReviewedClaim(claim_id="c1", paper_id="p1", summary="Finding A."),
            ],
        )
        assert len(result.consensus) == 1
        assert len(result.disagreements) == 1
        assert len(result.gaps) == 1

    def test_theme_review_result_allows_empty_disagreements(self) -> None:
        result = ThemeReviewResult(
            synthesis="All papers agree.",
            consensus=["Universal agreement on X."],
            disagreements=[],
            gaps=[],
            key_claims=[],
        )
        assert result.disagreements == []

    def test_theme_review_result_allows_empty_gaps(self) -> None:
        result = ThemeReviewResult(
            synthesis="Thorough coverage.",
            consensus=["Complete agreement."],
            disagreements=[],
            gaps=[],
            key_claims=[],
        )
        assert result.gaps == []

    def test_theme_review_result_requires_synthesis(self) -> None:
        with pytest.raises(Exception):
            ThemeReviewResult(
                synthesis="",
                consensus=["Something."],
            )

    def test_theme_review_result_requires_consensus(self) -> None:
        with pytest.raises(Exception):
            ThemeReviewResult(
                synthesis="A valid synthesis.",
                consensus=[],
            )


# --- Agent protocol tests ---


class TestAgentProtocol:
    def test_satisfies_protocol(self) -> None:
        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()
        assert isinstance(agent, Agent)


# --- Message building tests ---


class TestBuildMessage:
    def test_includes_theme_header(self) -> None:
        theme = {
            "id": "t1",
            "name": "Chronobiology",
            "description": "Study of biological rhythms.",
            "aliases": ["Circadian Biology", "Biological Rhythms"],
        }
        msg = _build_message(theme, [])
        assert "THEME: Chronobiology" in msg
        assert "DESCRIPTION: Study of biological rhythms." in msg
        assert "Circadian Biology" in msg
        assert "Biological Rhythms" in msg

    def test_groups_claims_by_paper(self) -> None:
        theme = {"id": "t1", "name": "X", "description": "Y"}
        claims = [
            {
                "id": "c1",
                "summary": "Claim A",
                "page": 1,
                "paragraph": 2,
                "deep": "Context A",
                "source": {"paper_id": "p1", "page": 1, "paragraph": 2},
            },
            {
                "id": "c2",
                "summary": "Claim B",
                "page": 3,
                "paragraph": 1,
                "deep": "Context B",
                "source": {"paper_id": "p2", "page": 3, "paragraph": 1},
            },
        ]
        msg = _build_message(theme, claims)
        assert "Paper: p1" in msg
        assert "Paper: p2" in msg
        assert "[c1]" in msg
        assert "[c2]" in msg

    def test_includes_claim_ids(self) -> None:
        theme = {"id": "t1", "name": "X", "description": "Y"}
        claims = [
            {
                "id": "uuid-123",
                "summary": "Finding",
                "page": 5,
                "paragraph": 3,
                "source": {"paper_id": "p1", "page": 5, "paragraph": 3},
            },
        ]
        msg = _build_message(theme, claims)
        assert "[uuid-123]" in msg

    def test_empty_claims(self) -> None:
        theme = {"id": "t1", "name": "X", "description": "Y"}
        msg = _build_message(theme, [])
        assert "THEME: X" in msg
        assert "0 paper(s)" in msg


# --- Agent run tests ---


@dataclass
class FakeRunOutput:
    content: Any


def _make_theme() -> dict[str, Any]:
    return {
        "id": "canonical-1",
        "name": "Chronobiology",
        "label": "Chronobiology",
        "description": "Study of biological rhythms across organisms.",
        "paper_ids": ["p1", "p2"],
        "aliases": ["Circadian Biology"],
        "source_theme_ids": ["st1", "st2"],
    }


def _make_claims() -> list[dict[str, Any]]:
    return [
        {
            "id": "c1",
            "theme_id": "st1",
            "theme_name": "Chronobiology",
            "text": "Circadian clock regulates metabolism.",
            "page": 2,
            "paragraph": 3,
            "deep": "[p.2,§3] The circadian clock plays a central role in metabolic regulation.",
            "summary": "Circadian clock regulates metabolism.",
            "source": {"paper_id": "p1", "page": 2, "paragraph": 3},
        },
        {
            "id": "c2",
            "theme_id": "st2",
            "theme_name": "Circadian Biology",
            "text": "Light exposure resets the SCN.",
            "page": 4,
            "paragraph": 1,
            "deep": "[p.4,§1] Light exposure is the primary zeitgeber for SCN resetting.",
            "summary": "Light resets the SCN clock.",
            "source": {"paper_id": "p2", "page": 4, "paragraph": 1},
        },
        {
            "id": "c3",
            "theme_id": "other-theme",
            "theme_name": "Gene Therapy",
            "text": "AAV vectors deliver cargo.",
            "page": 1,
            "paragraph": 1,
            "deep": "Irrelevant claim from same paper.",
            "summary": "AAV delivers cargo.",
            "source": {"paper_id": "p1", "page": 1, "paragraph": 1},
        },
    ]


def _make_review_result() -> ThemeReviewResult:
    return ThemeReviewResult(
        synthesis="Two papers demonstrate circadian regulation of metabolism and SCN resetting by light.",
        consensus=["Both papers confirm circadian rhythms influence physiology."],
        disagreements=["Paper 1 emphasizes metabolism, paper 2 focuses on neural mechanisms."],
        gaps=["No study examines circadian effects on immune function."],
        key_claims=[
            ReviewedClaim(claim_id="c1", paper_id="p1", summary="Clock regulates metabolism."),
            ReviewedClaim(claim_id="c2", paper_id="p2", summary="Light resets SCN."),
        ],
    )


class TestThemeReviewerAgentRun:
    @pytest.fixture
    def theme(self) -> dict[str, Any]:
        return _make_theme()

    @pytest.fixture
    def claims(self) -> list[dict[str, Any]]:
        return _make_claims()

    @pytest.fixture
    def mock_review(self) -> ThemeReviewResult:
        return _make_review_result()

    async def test_run_returns_correct_theme_id_and_label(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_review: ThemeReviewResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_review)

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"theme": theme, "claims": claims})

        assert result["theme_id"] == "canonical-1"
        assert result["label"] == "Chronobiology"

    async def test_run_returns_review_field_backward_compat(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_review: ThemeReviewResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_review)

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"theme": theme, "claims": claims})

        assert result["review"] == mock_review.synthesis
        assert isinstance(result["review"], str)

    async def test_run_returns_enriched_fields(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_review: ThemeReviewResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_review)

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"theme": theme, "claims": claims})

        assert result["consensus"] == mock_review.consensus
        assert result["disagreements"] == mock_review.disagreements
        assert result["gaps"] == mock_review.gaps

    async def test_run_returns_claim_ids_backward_compat(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_review: ThemeReviewResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_review)

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"theme": theme, "claims": claims})

        assert result["claim_ids"] == ["c1", "c2"]

    async def test_run_filters_claims_by_source_theme_ids(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_review: ThemeReviewResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_review)

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        await agent.run({"theme": theme, "claims": claims})

        # Verify message sent to LLM does NOT contain the Gene Therapy claim
        call_args = agent._agent.arun.call_args
        message = call_args[0][0]
        assert "c1" in message  # chronobiology claim
        assert "c2" in message  # circadian biology claim
        assert "AAV" not in message  # gene therapy claim filtered out

    async def test_run_filters_invalid_claim_ids_from_output(
        self, theme: dict[str, Any], claims: list[dict[str, Any]]
    ) -> None:
        # LLM returns a claim_id that doesn't exist in input
        review_with_invalid = ThemeReviewResult(
            synthesis="Analysis.",
            consensus=["Agreement."],
            key_claims=[
                ReviewedClaim(claim_id="c1", paper_id="p1", summary="Valid."),
                ReviewedClaim(claim_id="nonexistent", paper_id="p1", summary="Invalid."),
            ],
        )
        fake_output = FakeRunOutput(content=review_with_invalid)

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"theme": theme, "claims": claims})

        assert result["claim_ids"] == ["c1"]
        assert len(result["key_claims"]) == 1

    async def test_run_handles_empty_claims(
        self, theme: dict[str, Any]
    ) -> None:
        review_no_claims = ThemeReviewResult(
            synthesis="No claims available for analysis.",
            consensus=["Theme identified but no empirical claims found."],
            gaps=["Entire theme lacks empirical support in corpus."],
        )
        fake_output = FakeRunOutput(content=review_no_claims)

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"theme": theme, "claims": []})

        assert result["theme_id"] == "canonical-1"
        assert result["claim_ids"] == []
        assert len(result["gaps"]) == 1

    async def test_run_passes_output_schema_to_agno(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_review: ThemeReviewResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_review)

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        await agent.run({"theme": theme, "claims": claims})

        call_args = agent._agent.arun.call_args
        assert call_args[1]["output_schema"] is ThemeReviewResult
