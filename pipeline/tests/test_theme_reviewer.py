"""Tests for theme reviewer: Pydantic models, message builder, and batch run."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.agents.theme_reviewer import (
    BatchThemeReviewResult,
    ReviewedClaim,
    SingleThemeReview,
    ThemeReviewerAgent,
    _build_batch_message,
)

# --- Pydantic model tests ---


class TestPydanticModels:
    """Validate SingleThemeReview and BatchThemeReviewResult constraints."""

    def test_reviewed_claim_valid(self) -> None:
        """ReviewedClaim accepts valid fields."""
        claim = ReviewedClaim(
            claim_id="c1",
            paper_id="p1",
            summary="AAV9 achieves 80% transduction.",
        )
        assert claim.claim_id == "c1"
        assert claim.paper_id == "p1"

    def test_single_theme_review_valid(self) -> None:
        """SingleThemeReview accepts all fields including theme_name."""
        review = SingleThemeReview(
            theme_name="Chronobiology",
            synthesis="Theme X is well studied across three papers.",
            consensus=["Papers agree on mechanism A."],
            disagreements=["Paper 1 and 2 differ on dosage."],
            gaps=["No study addresses long-term effects."],
            key_claims=[
                ReviewedClaim(claim_id="c1", paper_id="p1", summary="Finding A."),
            ],
        )
        assert review.theme_name == "Chronobiology"
        assert len(review.consensus) == 1
        assert len(review.disagreements) == 1
        assert len(review.gaps) == 1

    def test_single_theme_review_allows_empty_disagreements(self) -> None:
        """Disagreements list can be empty."""
        review = SingleThemeReview(
            theme_name="Theme A",
            synthesis="All papers agree.",
            consensus=["Universal agreement on X."],
            disagreements=[],
            gaps=[],
            key_claims=[],
        )
        assert review.disagreements == []

    def test_single_theme_review_allows_empty_gaps(self) -> None:
        """Gaps list can be empty."""
        review = SingleThemeReview(
            theme_name="Theme A",
            synthesis="Thorough coverage.",
            consensus=["Complete agreement."],
            disagreements=[],
            gaps=[],
            key_claims=[],
        )
        assert review.gaps == []

    def test_single_theme_review_requires_synthesis(self) -> None:
        """Synthesis must be non-empty (min_length=1)."""
        with pytest.raises(Exception):
            SingleThemeReview(
                theme_name="Theme A",
                synthesis="",
                consensus=["Something."],
            )

    def test_single_theme_review_requires_consensus(self) -> None:
        """Consensus must have at least one entry (min_length=1)."""
        with pytest.raises(Exception):
            SingleThemeReview(
                theme_name="Theme A",
                synthesis="A valid synthesis.",
                consensus=[],
            )

    def test_batch_theme_review_result_valid(self) -> None:
        """BatchThemeReviewResult wraps a list of SingleThemeReview."""
        result = BatchThemeReviewResult(
            reviews=[
                SingleThemeReview(
                    theme_name="Theme A",
                    synthesis="Synthesis A.",
                    consensus=["Agreement A."],
                ),
            ],
        )
        assert len(result.reviews) == 1
        assert result.reviews[0].theme_name == "Theme A"

    def test_batch_theme_review_result_requires_reviews(self) -> None:
        """Reviews list must have at least one entry (min_length=1)."""
        with pytest.raises(Exception):
            BatchThemeReviewResult(reviews=[])


# --- Message building tests ---


class TestBuildBatchMessage:
    """Validate _build_batch_message output format."""

    def test_includes_theme_header(self) -> None:
        """Message includes theme name, description, and aliases."""
        themes = [
            {
                "id": "t1",
                "name": "Chronobiology",
                "description": "Study of biological rhythms.",
                "aliases": ["Circadian Biology", "Biological Rhythms"],
            },
        ]
        claims_per_theme: dict[str, list[dict[str, Any]]] = {"t1": []}
        msg = _build_batch_message(themes, claims_per_theme)
        assert "THEME 1: Chronobiology" in msg
        assert "DESCRIPTION: Study of biological rhythms." in msg
        assert "Circadian Biology" in msg
        assert "Biological Rhythms" in msg

    def test_groups_claims_by_paper(self) -> None:
        """Claims are grouped under their source paper."""
        themes = [{"id": "t1", "name": "X", "description": "Y"}]
        claims_per_theme = {
            "t1": [
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
            ],
        }
        msg = _build_batch_message(themes, claims_per_theme)
        assert "Paper: p1" in msg
        assert "Paper: p2" in msg
        assert "[c1]" in msg
        assert "[c2]" in msg

    def test_includes_claim_ids(self) -> None:
        """Claim IDs appear in bracket notation."""
        themes = [{"id": "t1", "name": "X", "description": "Y"}]
        claims_per_theme = {
            "t1": [
                {
                    "id": "uuid-123",
                    "summary": "Finding",
                    "page": 5,
                    "paragraph": 3,
                    "source": {"paper_id": "p1", "page": 5, "paragraph": 3},
                },
            ],
        }
        msg = _build_batch_message(themes, claims_per_theme)
        assert "[uuid-123]" in msg

    def test_empty_claims(self) -> None:
        """Theme with no claims shows 0 papers."""
        themes = [{"id": "t1", "name": "X", "description": "Y"}]
        claims_per_theme: dict[str, list[dict[str, Any]]] = {"t1": []}
        msg = _build_batch_message(themes, claims_per_theme)
        assert "THEME 1: X" in msg
        assert "0 paper(s)" in msg

    def test_multiple_themes_in_batch(self) -> None:
        """Batch message includes all themes with numbered headers."""
        themes = [
            {"id": "t1", "name": "Theme A", "description": "Desc A"},
            {"id": "t2", "name": "Theme B", "description": "Desc B"},
        ]
        claims_per_theme: dict[str, list[dict[str, Any]]] = {"t1": [], "t2": []}
        msg = _build_batch_message(themes, claims_per_theme)
        assert "THEME 1: Theme A" in msg
        assert "THEME 2: Theme B" in msg
        assert "Analyze the following 2 themes" in msg


# --- Agent run tests ---


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


def _make_batch_review_result() -> BatchThemeReviewResult:
    return BatchThemeReviewResult(
        reviews=[
            SingleThemeReview(
                theme_name="Chronobiology",
                synthesis="Two papers demonstrate circadian regulation of metabolism and SCN resetting by light.",
                consensus=["Both papers confirm circadian rhythms influence physiology."],
                disagreements=["Paper 1 emphasizes metabolism, paper 2 focuses on neural mechanisms."],
                gaps=["No study examines circadian effects on immune function."],
                key_claims=[
                    ReviewedClaim(claim_id="c1", paper_id="p1", summary="Clock regulates metabolism."),
                    ReviewedClaim(claim_id="c2", paper_id="p2", summary="Light resets SCN."),
                ],
            ),
        ],
    )


class TestThemeReviewerAgentRunBatch:
    """Test ThemeReviewerAgent.run_batch() by mocking run_agent_with_retry."""

    @pytest.fixture
    def theme(self) -> dict[str, Any]:
        return _make_theme()

    @pytest.fixture
    def claims(self) -> list[dict[str, Any]]:
        return _make_claims()

    @pytest.fixture
    def mock_batch_result(self) -> BatchThemeReviewResult:
        return _make_batch_review_result()

    async def test_run_batch_returns_correct_theme_id_and_label(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_batch_result: BatchThemeReviewResult
    ) -> None:
        """run_batch maps theme_name back to correct theme_id and label."""
        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = mock_batch_result
            results = await agent.run_batch([theme], claims)

        assert len(results) == 1
        assert results[0]["theme_id"] == "canonical-1"
        assert results[0]["label"] == "Chronobiology"

    async def test_run_batch_returns_review_field(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_batch_result: BatchThemeReviewResult
    ) -> None:
        """run_batch populates review field from synthesis."""
        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = mock_batch_result
            results = await agent.run_batch([theme], claims)

        assert results[0]["review"] == mock_batch_result.reviews[0].synthesis
        assert isinstance(results[0]["review"], str)

    async def test_run_batch_returns_enriched_fields(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_batch_result: BatchThemeReviewResult
    ) -> None:
        """run_batch includes consensus, disagreements, and gaps."""
        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = mock_batch_result
            results = await agent.run_batch([theme], claims)

        expected_review = mock_batch_result.reviews[0]
        assert results[0]["consensus"] == expected_review.consensus
        assert results[0]["disagreements"] == expected_review.disagreements
        assert results[0]["gaps"] == expected_review.gaps

    async def test_run_batch_returns_valid_claim_ids(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_batch_result: BatchThemeReviewResult
    ) -> None:
        """run_batch only includes claim IDs that exist in input claims."""
        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = mock_batch_result
            results = await agent.run_batch([theme], claims)

        assert results[0]["claim_ids"] == ["c1", "c2"]

    async def test_run_batch_filters_claims_by_source_theme_ids(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_batch_result: BatchThemeReviewResult
    ) -> None:
        """run_batch only passes claims matching source_theme_ids to the LLM."""
        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = mock_batch_result
            await agent.run_batch([theme], claims)

        # Verify message sent to LLM does NOT contain the Gene Therapy claim
        call_args = mock_retry.call_args
        message = call_args[0][1]  # second positional arg is the message string
        assert "c1" in message  # chronobiology claim
        assert "c2" in message  # circadian biology claim
        assert "AAV" not in message  # gene therapy claim filtered out

    async def test_run_batch_filters_invalid_claim_ids_from_output(
        self, theme: dict[str, Any], claims: list[dict[str, Any]]
    ) -> None:
        """run_batch removes claim IDs from output that don't exist in input."""
        review_with_invalid = BatchThemeReviewResult(
            reviews=[
                SingleThemeReview(
                    theme_name="Chronobiology",
                    synthesis="Analysis.",
                    consensus=["Agreement."],
                    key_claims=[
                        ReviewedClaim(claim_id="c1", paper_id="p1", summary="Valid."),
                        ReviewedClaim(claim_id="nonexistent", paper_id="p1", summary="Invalid."),
                    ],
                ),
            ],
        )

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = review_with_invalid
            results = await agent.run_batch([theme], claims)

        assert results[0]["claim_ids"] == ["c1"]
        assert len(results[0]["key_claims"]) == 1

    async def test_run_batch_handles_empty_claims(
        self, theme: dict[str, Any]
    ) -> None:
        """run_batch works when no claims are provided."""
        review_no_claims = BatchThemeReviewResult(
            reviews=[
                SingleThemeReview(
                    theme_name="Chronobiology",
                    synthesis="No claims available for analysis.",
                    consensus=["Theme identified but no empirical claims found."],
                    gaps=["Entire theme lacks empirical support in corpus."],
                ),
            ],
        )

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = review_no_claims
            results = await agent.run_batch([theme], [])

        assert results[0]["theme_id"] == "canonical-1"
        assert results[0]["claim_ids"] == []
        assert len(results[0]["gaps"]) == 1

    async def test_run_batch_passes_batch_theme_review_result_schema(
        self, theme: dict[str, Any], claims: list[dict[str, Any]], mock_batch_result: BatchThemeReviewResult
    ) -> None:
        """run_batch passes BatchThemeReviewResult as the expected model class."""
        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent()

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = mock_batch_result
            await agent.run_batch([theme], claims)

        call_args = mock_retry.call_args
        assert call_args[0][2] is BatchThemeReviewResult  # third positional arg is model class

    async def test_run_batch_splits_into_batches(self) -> None:
        """run_batch calls run_agent_with_retry once per batch of themes."""
        themes = [
            {"id": f"t{i}", "name": f"Theme {i}", "description": f"Desc {i}"}
            for i in range(7)
        ]
        # batch_size=5 means 2 batches: [5, 2]
        batch_result_5 = BatchThemeReviewResult(
            reviews=[
                SingleThemeReview(
                    theme_name=f"Theme {i}",
                    synthesis=f"Synthesis {i}.",
                    consensus=[f"Agreement {i}."],
                )
                for i in range(5)
            ],
        )
        batch_result_2 = BatchThemeReviewResult(
            reviews=[
                SingleThemeReview(
                    theme_name=f"Theme {i}",
                    synthesis=f"Synthesis {i}.",
                    consensus=[f"Agreement {i}."],
                )
                for i in range(5, 7)
            ],
        )

        with patch("pipeline.agents.theme_reviewer.AgnoAgent"):
            agent = ThemeReviewerAgent(batch_size=5)

        with patch("pipeline.agents.theme_reviewer.run_agent_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.side_effect = [batch_result_5, batch_result_2]
            results = await agent.run_batch(themes, [])

        assert mock_retry.call_count == 2
        assert len(results) == 7
