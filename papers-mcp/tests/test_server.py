"""Tests for papers_mcp.server MCP tool functions."""

from unittest.mock import MagicMock, patch

import pytest

from papers_mcp.schemas.results import (
    ClaimResult,
    ClaimSearchResult,
    ReviewSection,
    ThemeMapEntry,
    ThemeResult,
    ThemeReviewResult,
)
from papers_mcp.server import (
    get_claims_by_theme,
    get_literature_review,
    get_paper_themes,
    get_theme_map,
    get_theme_review,
    search_claims,
)

# --------------- constants ---------------

PAPER_ID = "paper-001"
THEME_NAME = "Attention Mechanisms"
THEME_ID = "theme-001"
CLAIM_TEXT = "Self-attention scales quadratically"
REVIEW_TEXT = "Papers agree that attention is key."
SECTION_TITLE = "Literature Review"
SCORE_HIGH = 0.95
SEARCH_QUERY = "attention mechanisms"
SEARCH_LIMIT = 5


# --------------- fixtures ---------------


@pytest.fixture()
def mock_store() -> MagicMock:
    """Provide a mocked PapersStore via get_store()."""
    with patch("papers_mcp.server.get_store") as mock_get:
        store = MagicMock()
        mock_get.return_value = store
        yield store


def _theme() -> ThemeResult:
    return ThemeResult(
        paper_id=PAPER_ID,
        name=THEME_NAME,
        description="Focus on attention",
    )


def _claim() -> ClaimResult:
    return ClaimResult(
        paper_id=PAPER_ID,
        theme_id=THEME_ID,
        theme_name=THEME_NAME,
        text=CLAIM_TEXT,
        page=1,
        paragraph=2,
    )


def _theme_map_entry() -> ThemeMapEntry:
    return ThemeMapEntry(
        name=THEME_NAME,
        description="Broad theme",
        paper_ids=[PAPER_ID],
        aliases=["Attn"],
    )


def _theme_review() -> ThemeReviewResult:
    return ThemeReviewResult(
        theme_id=THEME_ID,
        label=THEME_NAME,
        review=REVIEW_TEXT,
        consensus=["Agreed"],
        gaps=["Missing benchmarks"],
    )


def _review_section() -> ReviewSection:
    return ReviewSection(
        title=SECTION_TITLE,
        theme_id=THEME_ID,
        label=THEME_NAME,
        content="Section body text.",
    )


def _claim_search_result() -> ClaimSearchResult:
    return ClaimSearchResult(
        claim=_claim(),
        score=SCORE_HIGH,
    )


# --------------- get_paper_themes ---------------


class TestGetPaperThemes:
    """Tests for get_paper_themes tool."""

    def test_happy_path(self, mock_store: MagicMock) -> None:
        """Returns serialized theme dicts."""
        # Arrange
        mock_store.get_paper_themes.return_value = [_theme()]

        # Act
        result = get_paper_themes(PAPER_ID)

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == THEME_NAME
        assert result[0]["paper_id"] == PAPER_ID
        mock_store.get_paper_themes.assert_called_once_with(
            PAPER_ID,
        )

    def test_empty_results(self, mock_store: MagicMock) -> None:
        """No themes returns empty list."""
        # Arrange
        mock_store.get_paper_themes.return_value = []

        # Act
        result = get_paper_themes(PAPER_ID)

        # Assert
        assert result == []

    def test_multiple_themes(
        self,
        mock_store: MagicMock,
    ) -> None:
        """Multiple themes are serialized correctly."""
        # Arrange
        t1 = ThemeResult(
            paper_id=PAPER_ID,
            name="Theme A",
        )
        t2 = ThemeResult(
            paper_id=PAPER_ID,
            name="Theme B",
        )
        mock_store.get_paper_themes.return_value = [t1, t2]

        # Act
        result = get_paper_themes(PAPER_ID)

        # Assert
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"Theme A", "Theme B"}

    def test_serialization_keys(
        self,
        mock_store: MagicMock,
    ) -> None:
        """All ThemeResult fields appear in output dict."""
        # Arrange
        mock_store.get_paper_themes.return_value = [_theme()]

        # Act
        result = get_paper_themes(PAPER_ID)

        # Assert
        expected_keys = {
            "paper_id",
            "name",
            "description",
            "positions",
        }
        assert set(result[0].keys()) == expected_keys


# --------------- get_claims_by_theme ---------------


class TestGetClaimsByTheme:
    """Tests for get_claims_by_theme tool."""

    def test_happy_path(self, mock_store: MagicMock) -> None:
        """Returns serialized claim dicts."""
        # Arrange
        mock_store.get_claims_by_theme.return_value = [_claim()]

        # Act
        result = get_claims_by_theme(THEME_NAME)

        # Assert
        assert len(result) == 1
        assert result[0]["text"] == CLAIM_TEXT
        mock_store.get_claims_by_theme.assert_called_once_with(
            THEME_NAME,
        )

    def test_empty_results(self, mock_store: MagicMock) -> None:
        """No claims returns empty list."""
        # Arrange
        mock_store.get_claims_by_theme.return_value = []

        # Act
        result = get_claims_by_theme(THEME_NAME)

        # Assert
        assert result == []

    def test_claim_fields_serialized(
        self,
        mock_store: MagicMock,
    ) -> None:
        """All ClaimResult fields present in output."""
        # Arrange
        mock_store.get_claims_by_theme.return_value = [_claim()]

        # Act
        result = get_claims_by_theme(THEME_NAME)

        # Assert
        expected_keys = {
            "paper_id",
            "theme_id",
            "theme_name",
            "text",
            "page",
            "paragraph",
            "deep",
            "summary",
            "source",
        }
        assert set(result[0].keys()) == expected_keys


# --------------- get_theme_map ---------------


class TestGetThemeMap:
    """Tests for get_theme_map tool."""

    def test_happy_path(self, mock_store: MagicMock) -> None:
        """Returns serialized theme map entries."""
        # Arrange
        mock_store.get_theme_map.return_value = [
            _theme_map_entry(),
        ]

        # Act
        result = get_theme_map()

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == THEME_NAME
        assert result[0]["aliases"] == ["Attn"]

    def test_empty_results(self, mock_store: MagicMock) -> None:
        """Empty theme map returns empty list."""
        # Arrange
        mock_store.get_theme_map.return_value = []

        # Act
        result = get_theme_map()

        # Assert
        assert result == []


# --------------- get_theme_review ---------------


class TestGetThemeReview:
    """Tests for get_theme_review tool."""

    def test_happy_path(self, mock_store: MagicMock) -> None:
        """Returns serialized review dict when found."""
        # Arrange
        mock_store.get_theme_review.return_value = _theme_review()

        # Act
        result = get_theme_review(THEME_NAME)

        # Assert
        assert result is not None
        assert result["review"] == REVIEW_TEXT
        assert result["theme_id"] == THEME_ID
        mock_store.get_theme_review.assert_called_once_with(
            THEME_NAME,
        )

    def test_not_found(self, mock_store: MagicMock) -> None:
        """Returns None when no review exists."""
        # Arrange
        mock_store.get_theme_review.return_value = None

        # Act
        result = get_theme_review("Nonexistent")

        # Assert
        assert result is None

    def test_review_fields_serialized(
        self,
        mock_store: MagicMock,
    ) -> None:
        """All ThemeReviewResult fields appear in output."""
        # Arrange
        mock_store.get_theme_review.return_value = _theme_review()

        # Act
        result = get_theme_review(THEME_NAME)

        # Assert
        expected_keys = {
            "theme_id",
            "label",
            "review",
            "consensus",
            "disagreements",
            "gaps",
            "key_claims",
        }
        assert result is not None
        assert set(result.keys()) == expected_keys


# --------------- get_literature_review ---------------


class TestGetLiteratureReview:
    """Tests for get_literature_review tool."""

    def test_happy_path(self, mock_store: MagicMock) -> None:
        """Returns serialized review sections."""
        # Arrange
        mock_store.get_literature_review.return_value = [
            _review_section(),
        ]

        # Act
        result = get_literature_review()

        # Assert
        assert len(result) == 1
        assert result[0]["title"] == SECTION_TITLE
        assert result[0]["theme_id"] == THEME_ID

    def test_empty_results(self, mock_store: MagicMock) -> None:
        """No sections returns empty list."""
        # Arrange
        mock_store.get_literature_review.return_value = []

        # Act
        result = get_literature_review()

        # Assert
        assert result == []

    def test_section_fields_serialized(
        self,
        mock_store: MagicMock,
    ) -> None:
        """All ReviewSection fields appear in output."""
        # Arrange
        mock_store.get_literature_review.return_value = [
            _review_section(),
        ]

        # Act
        result = get_literature_review()

        # Assert
        expected_keys = {
            "title",
            "abstract",
            "theme_id",
            "label",
            "content",
            "claim_ids",
            "citation_refs",
            "citations",
            "references",
        }
        assert set(result[0].keys()) == expected_keys


# --------------- search_claims ---------------


class TestSearchClaims:
    """Tests for search_claims tool."""

    def test_happy_path(self, mock_store: MagicMock) -> None:
        """Returns serialized search results with scores."""
        # Arrange
        mock_store.search_claims.return_value = [
            _claim_search_result(),
        ]

        # Act
        result = search_claims(SEARCH_QUERY, SEARCH_LIMIT)

        # Assert
        assert len(result) == 1
        assert result[0]["score"] == SCORE_HIGH
        assert result[0]["claim"]["text"] == CLAIM_TEXT
        mock_store.search_claims.assert_called_once_with(
            SEARCH_QUERY,
            SEARCH_LIMIT,
        )

    def test_empty_results(self, mock_store: MagicMock) -> None:
        """No matches returns empty list."""
        # Arrange
        mock_store.search_claims.return_value = []

        # Act
        result = search_claims(SEARCH_QUERY)

        # Assert
        assert result == []

    def test_default_limit(
        self,
        mock_store: MagicMock,
    ) -> None:
        """Default limit of 10 is passed to store."""
        # Arrange
        mock_store.search_claims.return_value = []
        default_limit = 10

        # Act
        search_claims(SEARCH_QUERY)

        # Assert
        mock_store.search_claims.assert_called_once_with(
            SEARCH_QUERY,
            default_limit,
        )

    def test_multiple_results(
        self,
        mock_store: MagicMock,
    ) -> None:
        """Multiple search results are serialized."""
        # Arrange
        high_score = 0.95
        low_score = 0.70
        r1 = ClaimSearchResult(
            claim=_claim(),
            score=high_score,
        )
        r2 = ClaimSearchResult(
            claim=ClaimResult(
                paper_id="paper-002",
                text="Another claim",
            ),
            score=low_score,
        )
        mock_store.search_claims.return_value = [r1, r2]

        # Act
        result = search_claims(SEARCH_QUERY)

        # Assert
        assert len(result) == 2
        assert result[0]["score"] == high_score
        assert result[1]["score"] == low_score

    def test_store_error_propagates(
        self,
        mock_store: MagicMock,
    ) -> None:
        """Store exceptions propagate (error handling is in store)."""
        # Arrange
        mock_store.search_claims.side_effect = RuntimeError(
            "embed failed",
        )

        # Act / Assert
        with pytest.raises(RuntimeError):
            search_claims(SEARCH_QUERY)
