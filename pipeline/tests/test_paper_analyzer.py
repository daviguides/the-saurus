"""Tests for paper analyzer agent: Pydantic models, output splitting, protocol."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from pipeline.agents.gate import TopicGateResult
from pipeline.agents.paper_analyzer import (
    ClaimPosition,
    ExtractedClaim,
    PaperAnalysisResult,
    PaperAnalyzerAgent,
    ThemeWithClaims,
    _grounding_scores,
    _pack_under_budget,
    merge_chunk_results,
)
from pipeline.agents.prompts.paper_analyzer import PAPER_ANALYZER_PROMPT
from pipeline.agents.protocol import Agent
from pipeline.config import settings
from pipeline.core.exceptions import TopicGateRejectedError

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
    themes = [_make_theme(name=f"Theme {i}") for i in range(num_themes)]
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

    @pytest.fixture(autouse=True)
    def _gate_accepts_by_default(self):
        """These tests exercise output-splitting, not the topic gate — default
        the gate to accept so short/metadata-less fixtures don't reject before
        run_agent_with_retry is reached. Gate-specific tests below override."""
        mock_gate = AsyncMock(return_value=TopicGateResult(verdict="accept"))
        with patch("pipeline.agents.paper_analyzer.evaluate_topic_gate", mock_gate):
            yield mock_gate

    @pytest.fixture(autouse=True)
    def _grounded_by_default(self):
        """These tests exercise output-splitting, not provenance grounding —
        default embed_batch/cosine_similarity so every claim passes threshold
        and reask is never triggered. Provenance-specific tests live in
        TestPaperAnalyzerProvenance below."""
        mock_embed_batch = AsyncMock(side_effect=lambda texts: [[1.0] for _ in texts])
        with (
            patch("pipeline.agents.paper_analyzer.embed_batch", mock_embed_batch),
            patch("pipeline.agents.paper_analyzer.cosine_similarity", return_value=1.0),
        ):
            yield

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
        assert all(t["paper_id"] == PAPER_ID for t in result["themes"])

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

    @pytest.mark.asyncio
    async def test_run_raises_and_skips_llm_when_gate_rejects(
        self,
        _gate_accepts_by_default,
    ) -> None:
        """A gate rejection raises TopicGateRejectedError before the LLM call."""
        # Arrange
        _gate_accepts_by_default.return_value = TopicGateResult(
            verdict="reject",
            reason="quality_or_metadata",
        )
        mock_retry = AsyncMock(return_value=_make_analysis(num_themes=1))

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "short",
            "title": "",
            "authors": [],
            "page_count": 1,
        }

        with patch(
            "pipeline.agents.paper_analyzer.run_agent_with_retry",
            mock_retry,
        ):
            agent = PaperAnalyzerAgent()

            # Act / Assert
            with pytest.raises(TopicGateRejectedError) as exc_info:
                await agent.run(input_data)

        assert exc_info.value.reason == "quality_or_metadata"
        mock_retry.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_proceeds_to_llm_when_gate_accepts(
        self,
        _gate_accepts_by_default,
    ) -> None:
        """A gate acceptance lets run_agent_with_retry get called normally."""
        # Arrange
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Full paper text here.",
            "title": "Test Paper",
            "authors": ["Author A"],
            "page_count": 3,
        }

        with patch(
            "pipeline.agents.paper_analyzer.run_agent_with_retry",
            mock_retry,
        ):
            agent = PaperAnalyzerAgent()

            # Act
            result = await agent.run(input_data)

        # Assert
        mock_retry.assert_called_once()
        assert "themes" in result


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
            "t1",
            "Gene Therapy",
            positions=[{"page": 1, "paragraph": 1}],
        )
        chunk2 = _make_chunk_result(
            "t2",
            "gene therapy",
            positions=[{"page": 1, "paragraph": 1}, {"page": 5, "paragraph": 2}],
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


# --- _pack_under_budget ---


class TestPackUnderBudget:
    """Validate the local greedy re-split fallback for over-budget content."""

    @pytest.mark.asyncio
    async def test_single_block_passthrough(self) -> None:
        """Content with no blank-line separators stays a single sub-chunk."""
        content = "Full paper text here."

        with patch(
            "pipeline.agents.paper_analyzer.count_tokens",
            AsyncMock(return_value=200),
        ):
            result = await _pack_under_budget(content, 10)

        assert result == [content]

    @pytest.mark.asyncio
    async def test_blocks_under_budget_stay_together(self) -> None:
        """Blocks that together fit under budget are not split."""
        blocks = ["Block one.", "Block two."]
        content = "\n\n".join(blocks)

        with patch(
            "pipeline.agents.paper_analyzer.count_tokens",
            AsyncMock(side_effect=[10, 10]),
        ):
            result = await _pack_under_budget(content, 100)

        assert result == [content]

    @pytest.mark.asyncio
    async def test_greedy_packing_splits_at_budget_boundary(self) -> None:
        """Blocks are grouped greedily, splitting once the running total
        would exceed budget."""
        blocks = ["Block one.", "Block two.", "Block three."]
        content = "\n\n".join(blocks)

        with patch(
            "pipeline.agents.paper_analyzer.count_tokens",
            AsyncMock(side_effect=[10, 10, 10]),
        ):
            result = await _pack_under_budget(content, 25)

        assert result == ["Block one.\n\nBlock two.", "Block three."]

    @pytest.mark.asyncio
    async def test_oversized_single_block_forwarded_not_dropped(self) -> None:
        """A block that alone exceeds budget is forwarded as-is, not
        truncated or dropped — no silent-truncation path exists."""
        content = "One enormous paragraph that alone busts the budget."

        with patch(
            "pipeline.agents.paper_analyzer.count_tokens",
            AsyncMock(return_value=9999),
        ):
            result = await _pack_under_budget(content, 10)

        assert result == [content]

    @pytest.mark.asyncio
    async def test_empty_content_returns_content_as_single_element(self) -> None:
        """Blank/whitespace-only content produces a one-element passthrough
        rather than an empty list."""
        with patch(
            "pipeline.agents.paper_analyzer.count_tokens",
            AsyncMock(return_value=0),
        ):
            result = await _pack_under_budget("   ", 10)

        assert result == ["   "]


# --- Token-budget enforcement in run() (§4.1 CWM) ---


class TestPaperAnalyzerRunBudget:
    """Test PaperAnalyzerAgent.run()'s pre-call token-budget check and its
    over-budget chunk-and-merge branch."""

    @pytest.fixture(autouse=True)
    def _gate_accepts_by_default(self):
        mock_gate = AsyncMock(return_value=TopicGateResult(verdict="accept"))
        with patch("pipeline.agents.paper_analyzer.evaluate_topic_gate", mock_gate):
            yield mock_gate

    @pytest.mark.asyncio
    async def test_under_budget_takes_single_call_path(self) -> None:
        """Content under budget results in exactly one run_agent_with_retry call."""
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Short content.",
        }

        with (
            patch(
                "pipeline.agents.paper_analyzer.run_agent_with_retry",
                mock_retry,
            ),
            patch(
                "pipeline.agents.paper_analyzer.count_tokens",
                AsyncMock(return_value=10),
            ),
        ):
            agent = PaperAnalyzerAgent()
            result = await agent.run(input_data)

        mock_retry.assert_called_once()
        assert "themes" in result

    @pytest.mark.asyncio
    async def test_budget_check_counts_prompt_and_content_together(self) -> None:
        """The budget check measures PAPER_ANALYZER_PROMPT alongside content,
        not content alone."""
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)
        mock_count = AsyncMock(return_value=10)

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Short content.",
        }

        with (
            patch(
                "pipeline.agents.paper_analyzer.run_agent_with_retry",
                mock_retry,
            ),
            patch(
                "pipeline.agents.paper_analyzer.count_tokens",
                mock_count,
            ),
        ):
            agent = PaperAnalyzerAgent()
            await agent.run(input_data)

        counted_args = [c.args[0] for c in mock_count.await_args_list]
        assert PAPER_ANALYZER_PROMPT in counted_args
        assert "Short content." in counted_args

    @pytest.mark.asyncio
    async def test_over_budget_splits_into_multiple_calls_and_merges(self) -> None:
        """Content over budget is packed into sub-chunks, each gets its own
        run_agent_with_retry call, and results are merged — not truncated."""
        theme_a = _make_theme(name="Theme A")
        theme_b = _make_theme(name="Theme B")
        mock_retry = AsyncMock(
            side_effect=[
                PaperAnalysisResult(themes=[theme_a]),
                PaperAnalysisResult(themes=[theme_b]),
            ],
        )

        input_data: dict[str, Any] = {
            "paper_id": PAPER_ID,
            "content": "Block one.\n\nBlock two.",
        }

        with (
            patch(
                "pipeline.agents.paper_analyzer.run_agent_with_retry",
                mock_retry,
            ),
            patch(
                "pipeline.agents.paper_analyzer.count_tokens",
                AsyncMock(return_value=9000),
            ),
            patch(
                "pipeline.agents.paper_analyzer._pack_under_budget",
                AsyncMock(return_value=["Block one.", "Block two."]),
            ),
            patch(
                "pipeline.agents.paper_analyzer.embed_batch",
                AsyncMock(side_effect=lambda texts: [[1.0] for _ in texts]),
            ),
            patch("pipeline.agents.paper_analyzer.cosine_similarity", return_value=0.9),
        ):
            agent = PaperAnalyzerAgent()
            result = await agent.run(input_data)

        assert mock_retry.call_count == 2
        theme_names = {t["name"] for t in result["themes"]}
        assert theme_names == {"Theme A", "Theme B"}
        assert len(result["claims"]) == 2


# --- Provenance grounding (_grounding_scores / _enforce_provenance / _drop_ungrounded) ---


class TestGroundingScores:
    """Unit tests for _grounding_scores: batches text+deep into one embed call."""

    @pytest.mark.asyncio
    async def test_batches_single_embed_call_in_text_then_deep_order(self) -> None:
        claims = [
            _make_claim(text="Claim A", page=1, paragraph=1),
            _make_claim(text="Claim B", page=2, paragraph=2),
        ]
        mock_embed_batch = AsyncMock(return_value=[[1.0], [1.0], [1.0], [1.0]])

        with (
            patch("pipeline.agents.paper_analyzer.embed_batch", mock_embed_batch),
            patch("pipeline.agents.paper_analyzer.cosine_similarity", return_value=0.42),
        ):
            scores = await _grounding_scores(claims)

        mock_embed_batch.assert_awaited_once_with(["Claim A", "Claim B", CLAIM_DEEP, CLAIM_DEEP])
        assert scores == [0.42, 0.42]

    @pytest.mark.asyncio
    async def test_empty_claims_returns_empty_without_calling_embed(self) -> None:
        mock_embed_batch = AsyncMock()

        with patch("pipeline.agents.paper_analyzer.embed_batch", mock_embed_batch):
            scores = await _grounding_scores([])

        assert scores == []
        mock_embed_batch.assert_not_called()


class TestPaperAnalyzerProvenance:
    """Test PaperAnalyzerAgent.run()'s extraction-time grounding check."""

    @pytest.fixture(autouse=True)
    def _gate_accepts(self):
        mock_gate = AsyncMock(return_value=TopicGateResult(verdict="accept"))
        with patch("pipeline.agents.paper_analyzer.evaluate_topic_gate", mock_gate):
            yield mock_gate

    @pytest.mark.asyncio
    async def test_no_reask_when_all_claims_grounded(self) -> None:
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)
        mock_reask = AsyncMock()
        mock_embed_batch = AsyncMock(side_effect=lambda texts: [[1.0] for _ in texts])

        with (
            patch("pipeline.agents.paper_analyzer.run_agent_with_retry", mock_retry),
            patch("pipeline.agents.paper_analyzer.reask", mock_reask),
            patch("pipeline.agents.paper_analyzer.embed_batch", mock_embed_batch),
            patch("pipeline.agents.paper_analyzer.cosine_similarity", return_value=0.9),
        ):
            agent = PaperAnalyzerAgent()
            result = await agent.run({"paper_id": PAPER_ID, "content": "text"})

        mock_reask.assert_not_called()
        assert len(result["claims"]) == 1

    @pytest.mark.asyncio
    async def test_reask_correction_keeps_claim(self) -> None:
        """A flagged claim survives if the reask-corrected result re-passes the check."""
        analysis = _make_analysis(num_themes=1)
        corrected = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)
        mock_reask = AsyncMock(return_value=corrected)
        mock_embed_batch = AsyncMock(side_effect=lambda texts: [[1.0] for _ in texts])

        with (
            patch("pipeline.agents.paper_analyzer.run_agent_with_retry", mock_retry),
            patch("pipeline.agents.paper_analyzer.reask", mock_reask),
            patch("pipeline.agents.paper_analyzer.embed_batch", mock_embed_batch),
            patch(
                "pipeline.agents.paper_analyzer.cosine_similarity",
                side_effect=[0.3, 0.9],
            ),
        ):
            agent = PaperAnalyzerAgent()
            result = await agent.run({"paper_id": PAPER_ID, "content": "text"})

        mock_reask.assert_awaited_once()
        assert len(result["claims"]) == 1

    @pytest.mark.asyncio
    async def test_reask_exhausted_drops_claim_and_logs(self, caplog) -> None:
        """A claim still ungrounded after reask is dropped from the output and logged."""
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)
        # Simulates reask()'s own fallback path: returns the original, uncorrected result.
        mock_reask = AsyncMock(return_value=analysis)
        mock_embed_batch = AsyncMock(side_effect=lambda texts: [[1.0] for _ in texts])

        with (
            patch("pipeline.agents.paper_analyzer.run_agent_with_retry", mock_retry),
            patch("pipeline.agents.paper_analyzer.reask", mock_reask),
            patch("pipeline.agents.paper_analyzer.embed_batch", mock_embed_batch),
            patch(
                "pipeline.agents.paper_analyzer.cosine_similarity",
                side_effect=[0.3, 0.3],
            ),
            caplog.at_level("WARNING"),
        ):
            agent = PaperAnalyzerAgent()
            result = await agent.run({"paper_id": PAPER_ID, "content": "text"})

        mock_reask.assert_awaited_once()
        assert result["claims"] == []
        assert len(result["themes"]) == 1  # theme itself is kept, just empty of claims
        assert "Provenance check dropped claim" in caplog.text

    @pytest.mark.asyncio
    async def test_threshold_is_configurable(self) -> None:
        """A lowered threshold accepts a claim that would otherwise be flagged."""
        analysis = _make_analysis(num_themes=1)
        mock_retry = AsyncMock(return_value=analysis)
        mock_reask = AsyncMock()
        mock_embed_batch = AsyncMock(side_effect=lambda texts: [[1.0] for _ in texts])

        with (
            patch("pipeline.agents.paper_analyzer.run_agent_with_retry", mock_retry),
            patch("pipeline.agents.paper_analyzer.reask", mock_reask),
            patch("pipeline.agents.paper_analyzer.embed_batch", mock_embed_batch),
            patch("pipeline.agents.paper_analyzer.cosine_similarity", return_value=0.5),
            patch.object(settings, "provenance_similarity_threshold", 0.1),
        ):
            agent = PaperAnalyzerAgent()
            result = await agent.run({"paper_id": PAPER_ID, "content": "text"})

        mock_reask.assert_not_called()
        assert len(result["claims"]) == 1


# --- Protocol compliance ---


class TestProtocolCompliance:
    """Verify PaperAnalyzerAgent satisfies the Agent protocol."""

    def test_satisfies_agent_protocol(self) -> None:
        """PaperAnalyzerAgent is a runtime-checkable Agent."""
        # Arrange / Act
        agent = PaperAnalyzerAgent()

        # Assert
        assert isinstance(agent, Agent)
