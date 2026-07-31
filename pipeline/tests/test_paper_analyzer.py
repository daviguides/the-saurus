"""Tests for paper analyzer agent: Pydantic models, output splitting, protocol."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from pipeline.agents.paper_analyzer import (
    ClaimPosition,
    ExtractedClaim,
    PaperAnalysisResult,
    PaperAnalyzerAgent,
    ThemeWithClaims,
    merge_chunk_results,
)
from pipeline.agents.protocol import Agent

# --- Constants ---

VALID_PAGE = 3
VALID_PARAGRAPH = 7
PAPER_ID = "paper-001"
THEME_NAME = "Gene Therapy Vectors"
THEME_DESCRIPTION = "Comparison of AAV serotypes for CNS delivery."
CLAIM_TEXT = "AAV9 crosses the blood-brain barrier."
CLAIM_DEEP = "AAV9 demonstrated 80% transduction efficiency."
CLAIM_SUMMARY = "AAV9 is effective for CNS gene delivery."


# --- Helpers ---


def _make_position(
    page: int = VALID_PAGE,
    paragraph: int = VALID_PARAGRAPH,
) -> ClaimPosition:
    """Build a valid ClaimPosition."""
    return ClaimPosition(page=page, paragraph=paragraph)


def _make_claim(
    text: str = CLAIM_TEXT,
    page: int = VALID_PAGE,
    paragraph: int = VALID_PARAGRAPH,
) -> ExtractedClaim:
    """Build a valid ExtractedClaim."""
    return ExtractedClaim(
        text=text,
        position=_make_position(page, paragraph),
        deep=CLAIM_DEEP,
        summary=CLAIM_SUMMARY,
    )


def _make_theme(
    name: str = THEME_NAME,
    num_claims: int = 1,
) -> ThemeWithClaims:
    """Build a valid ThemeWithClaims with N claims."""
    claims = [_make_claim(text=f"Claim {i}") for i in range(num_claims)]
    positions = [_make_position(page=i + 1) for i in range(num_claims)]
    return ThemeWithClaims(
        name=name,
        description=THEME_DESCRIPTION,
        positions=positions,
        claims=claims,
    )


def _make_analysis(num_themes: int = 1) -> PaperAnalysisResult:
    """Build a valid PaperAnalysisResult."""
    themes = [
        _make_theme(name=f"Theme {i}")
        for i in range(num_themes)
    ]
    return PaperAnalysisResult(themes=themes)


# --- Pydantic model tests ---


class TestClaimPosition:
    """Validate ClaimPosition model."""

    def test_valid_position(self) -> None:
        """ClaimPosition accepts valid page and paragraph."""
        # Arrange / Act
        pos = _make_position()

        # Assert
        assert pos.page == VALID_PAGE
        assert pos.paragraph == VALID_PARAGRAPH

    def test_zero_page_accepted(self) -> None:
        """Page zero is a valid value (zero-indexed)."""
        pos = _make_position(page=0)
        assert pos.page == 0

    def test_negative_page_accepted(self) -> None:
        """Model does not restrict negative values (no validator)."""
        pos = _make_position(page=-1)
        assert pos.page == -1


class TestExtractedClaim:
    """Validate ExtractedClaim model."""

    def test_valid_claim(self) -> None:
        """ExtractedClaim accepts all required fields."""
        claim = _make_claim()
        assert claim.text == CLAIM_TEXT
        assert claim.position.page == VALID_PAGE
        assert claim.deep == CLAIM_DEEP
        assert claim.summary == CLAIM_SUMMARY

    def test_missing_text_raises(self) -> None:
        """Omitting required text field raises ValidationError."""
        with pytest.raises(ValidationError):
            ExtractedClaim(
                position=_make_position(),
                deep=CLAIM_DEEP,
                summary=CLAIM_SUMMARY,
            )  # type: ignore[call-arg]

    def test_missing_position_raises(self) -> None:
        """Omitting required position field raises ValidationError."""
        with pytest.raises(ValidationError):
            ExtractedClaim(
                text=CLAIM_TEXT,
                deep=CLAIM_DEEP,
                summary=CLAIM_SUMMARY,
            )  # type: ignore[call-arg]


class TestThemeWithClaims:
    """Validate ThemeWithClaims model constraints."""

    def test_valid_theme(self) -> None:
        """ThemeWithClaims accepts valid fields with min_length=1 lists."""
        theme = _make_theme()
        assert theme.name == THEME_NAME
        assert theme.description == THEME_DESCRIPTION
        assert len(theme.positions) == 1
        assert len(theme.claims) == 1

    def test_multiple_claims(self) -> None:
        """ThemeWithClaims accepts multiple claims and positions."""
        num_claims = 5
        theme = _make_theme(num_claims=num_claims)
        assert len(theme.claims) == num_claims
        assert len(theme.positions) == num_claims

    def test_empty_positions_raises(self) -> None:
        """Positions list with min_length=1 rejects empty list."""
        with pytest.raises(ValidationError, match="positions"):
            ThemeWithClaims(
                name=THEME_NAME,
                description=THEME_DESCRIPTION,
                positions=[],
                claims=[_make_claim()],
            )

    def test_empty_claims_raises(self) -> None:
        """Claims list with min_length=1 rejects empty list."""
        with pytest.raises(ValidationError, match="claims"):
            ThemeWithClaims(
                name=THEME_NAME,
                description=THEME_DESCRIPTION,
                positions=[_make_position()],
                claims=[],
            )


class TestPaperAnalysisResult:
    """Validate PaperAnalysisResult model constraints."""

    def test_valid_result(self) -> None:
        """PaperAnalysisResult accepts a non-empty themes list."""
        result = _make_analysis(num_themes=2)
        assert len(result.themes) == 2

    def test_empty_themes_raises(self) -> None:
        """Themes list with min_length=1 rejects empty list."""
        with pytest.raises(ValidationError, match="themes"):
            PaperAnalysisResult(themes=[])


# --- Output splitting in run() ---


class TestPaperAnalyzerRun:
    """Test PaperAnalyzerAgent.run() output splitting logic."""

    @pytest.mark.asyncio
    async def test_run_splits_themes_and_claims(self) -> None:
        """run() splits PaperAnalysisResult into themes and claims dicts."""
        # Arrange
        analysis = _make_analysis(num_themes=2)
        mock_retry = AsyncMock(return_value=analysis)

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Full paper text here.",
            "title": "Test Paper",
        }

        with patch(
            "pipeline.agents.paper_analyzer.run_agent_with_retry",
            mock_retry,
        ):
            agent = PaperAnalyzerAgent()

            # Act
            result = await agent.run(input_data)

        # Assert
        assert "themes" in result
        assert "claims" in result
        assert len(result["themes"]) == 2
        assert all(
            t["paper_id"] == PAPER_ID for t in result["themes"]
        )

    @pytest.mark.asyncio
    async def test_run_claims_reference_theme_ids(self) -> None:
        """Each claim's theme_id matches its parent theme's id."""
        # Arrange
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Paper content.",
        }

        with patch(
            "pipeline.agents.paper_analyzer.run_agent_with_retry",
            mock_retry,
        ):
            agent = PaperAnalyzerAgent()

            # Act
            result = await agent.run(input_data)

        # Assert
        theme_id = result["themes"][0]["id"]
        for claim in result["claims"]:
            assert claim["theme_id"] == theme_id

    @pytest.mark.asyncio
    async def test_run_claim_source_structure(self) -> None:
        """Each claim includes a source dict with paper_id, page, paragraph."""
        # Arrange
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Paper content.",
        }

        with patch(
            "pipeline.agents.paper_analyzer.run_agent_with_retry",
            mock_retry,
        ):
            agent = PaperAnalyzerAgent()

            # Act
            result = await agent.run(input_data)

        # Assert
        claim = result["claims"][0]
        assert claim["source"]["paper_id"] == PAPER_ID
        assert "page" in claim["source"]
        assert "paragraph" in claim["source"]

    @pytest.mark.asyncio
    async def test_run_multiple_themes_multiple_claims(self) -> None:
        """Multiple themes with multiple claims each produce correct counts."""
        # Arrange
        claims_per_theme = 3
        num_themes = 2
        themes = [
            _make_theme(
                name=f"Theme {i}",
                num_claims=claims_per_theme,
            )
            for i in range(num_themes)
        ]
        analysis = PaperAnalysisResult(themes=themes)
        mock_retry = AsyncMock(return_value=analysis)

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Paper content.",
        }

        with patch(
            "pipeline.agents.paper_analyzer.run_agent_with_retry",
            mock_retry,
        ):
            agent = PaperAnalyzerAgent()

            # Act
            result = await agent.run(input_data)

        # Assert
        expected_claims = num_themes * claims_per_theme
        assert len(result["themes"]) == num_themes
        assert len(result["claims"]) == expected_claims

    @pytest.mark.asyncio
    async def test_run_theme_positions_serialized(self) -> None:
        """Theme positions are serialized via model_dump()."""
        # Arrange
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Paper content.",
        }

        with patch(
            "pipeline.agents.paper_analyzer.run_agent_with_retry",
            mock_retry,
        ):
            agent = PaperAnalyzerAgent()

            # Act
            result = await agent.run(input_data)

        # Assert
        positions = result["themes"][0]["positions"]
        assert isinstance(positions, list)
        assert isinstance(positions[0], dict)
        assert "page" in positions[0]
        assert "paragraph" in positions[0]


# --- merge_chunk_results ---


def _make_chunk_result(
    theme_id: str,
    theme_name: str,
    *,
    positions: list[dict[str, int]] | None = None,
    claim_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a single-theme chunk result in PaperAnalyzerAgent.run()'s output shape."""
    positions = positions or [{"page": 1, "paragraph": 1}]
    claim_ids = claim_ids or [f"{theme_id}-claim-0"]
    return {
        "themes": [
            {
                "id": theme_id,
                "name": theme_name,
                "description": THEME_DESCRIPTION,
                "paper_id": PAPER_ID,
                "positions": positions,
            }
        ],
        "claims": [
            {
                "id": cid,
                "theme_id": theme_id,
                "theme_name": theme_name,
                "text": CLAIM_TEXT,
                "page": VALID_PAGE,
                "paragraph": VALID_PARAGRAPH,
                "deep": CLAIM_DEEP,
                "summary": CLAIM_SUMMARY,
                "source": {"paper_id": PAPER_ID, "page": VALID_PAGE, "paragraph": VALID_PARAGRAPH},
            }
            for cid in claim_ids
        ],
    }


class TestMergeChunkResults:
    """Validate cross-chunk theme reconciliation."""

    def test_single_chunk_returns_data_unchanged(self) -> None:
        """A single chunk result passes through with the same theme/claim ids."""
        chunk = _make_chunk_result("t1", "Gene Therapy")

        merged = merge_chunk_results([chunk])

        assert merged["themes"] == chunk["themes"]
        assert merged["claims"] == chunk["claims"]

    def test_same_normalized_name_merges_into_one_theme(self) -> None:
        """Two chunks with the same (normalized) theme name merge into one."""
        chunk1 = _make_chunk_result("t1", "Gene Therapy Vectors", claim_ids=["c1"])
        chunk2 = _make_chunk_result("t2", "gene-therapy_vectors", claim_ids=["c2"])

        merged = merge_chunk_results([chunk1, chunk2])

        assert len(merged["themes"]) == 1
        assert merged["themes"][0]["id"] == "t1"  # first occurrence is canonical
        assert len(merged["claims"]) == 2

    def test_merged_positions_are_unioned(self) -> None:
        """Positions from both chunks are combined, duplicates removed."""
        chunk1 = _make_chunk_result(
            "t1", "Gene Therapy", positions=[{"page": 1, "paragraph": 1}],
        )
        chunk2 = _make_chunk_result(
            "t2", "gene therapy", positions=[{"page": 1, "paragraph": 1}, {"page": 5, "paragraph": 2}],
        )

        merged = merge_chunk_results([chunk1, chunk2])

        positions = merged["themes"][0]["positions"]
        assert {"page": 1, "paragraph": 1} in positions
        assert {"page": 5, "paragraph": 2} in positions
        assert len(positions) == 2  # the duplicate position was not re-added

    def test_claims_remapped_to_canonical_theme_id(self) -> None:
        """Claims from the non-canonical chunk get the canonical theme_id."""
        chunk1 = _make_chunk_result("t1", "Gene Therapy", claim_ids=["c1"])
        chunk2 = _make_chunk_result("t2", "Gene Therapy", claim_ids=["c2"])

        merged = merge_chunk_results([chunk1, chunk2])

        assert all(c["theme_id"] == "t1" for c in merged["claims"])

    def test_distinct_theme_names_stay_separate(self) -> None:
        """Chunks with genuinely different theme names produce separate themes."""
        chunk1 = _make_chunk_result("t1", "Gene Therapy")
        chunk2 = _make_chunk_result("t2", "Neural Plasticity")

        merged = merge_chunk_results([chunk1, chunk2])

        assert len(merged["themes"]) == 2
        theme_ids = {t["id"] for t in merged["themes"]}
        assert theme_ids == {"t1", "t2"}

    def test_empty_chunk_contributes_nothing(self) -> None:
        """A chunk with no themes/claims (e.g. references-only) doesn't error."""
        chunk1 = _make_chunk_result("t1", "Gene Therapy")
        empty_chunk: dict[str, Any] = {"themes": [], "claims": []}

        merged = merge_chunk_results([chunk1, empty_chunk])

        assert len(merged["themes"]) == 1
        assert len(merged["claims"]) == 1

    def test_all_chunks_empty_returns_empty_result(self) -> None:
        """No themes across any chunk yields an empty (not erroring) result."""
        merged = merge_chunk_results([{"themes": [], "claims": []}])

        assert merged == {"themes": [], "claims": []}


# --- Protocol compliance ---


class TestProtocolCompliance:
    """Verify PaperAnalyzerAgent satisfies the Agent protocol."""

    def test_satisfies_agent_protocol(self) -> None:
        """PaperAnalyzerAgent is a runtime-checkable Agent."""
        # Arrange / Act
        agent = PaperAnalyzerAgent()

        # Assert
        assert isinstance(agent, Agent)
