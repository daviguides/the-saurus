"""Tests for papers_mcp.store module."""

from types import SimpleNamespace
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
from papers_mcp.store import (
    PapersStore,
    _SCROLL_LIMIT,
    get_store,
)

# --------------- constants ---------------

PAPER_ID = "paper-001"
THEME_NAME = "Attention Mechanisms"
THEME_ID = "theme-001"
CLAIM_TEXT = "Self-attention scales quadratically"
REVIEW_TEXT = "Papers agree that attention is key."
SECTION_TITLE = "Literature Review"
SCORE_HIGH = 0.95
SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 10
EMBEDDING_DIM = 3
FAKE_EMBEDDING = [0.1, 0.2, 0.3]


# --------------- fixtures ---------------


def _make_record(payload: dict) -> SimpleNamespace:
    """Build a minimal Qdrant-like record object."""
    return SimpleNamespace(payload=payload)


def _theme_payload(
    paper_id: str = PAPER_ID,
    name: str = THEME_NAME,
) -> dict:
    return {
        "paper_id": paper_id,
        "name": name,
        "description": "Focus on attention",
    }


def _claim_payload(
    paper_id: str = PAPER_ID,
    theme_name: str = THEME_NAME,
    text: str = CLAIM_TEXT,
) -> dict:
    return {
        "paper_id": paper_id,
        "theme_id": THEME_ID,
        "theme_name": theme_name,
        "text": text,
        "page": 1,
        "paragraph": 2,
    }


def _theme_map_payload(name: str = THEME_NAME) -> dict:
    return {
        "name": name,
        "description": "Broad theme",
        "paper_ids": [PAPER_ID],
        "aliases": ["Attn"],
    }


def _theme_review_payload(
    label: str = THEME_NAME,
) -> dict:
    return {
        "theme_id": THEME_ID,
        "label": label,
        "review": REVIEW_TEXT,
        "consensus": ["Agreed"],
        "disagreements": [],
        "gaps": ["Missing benchmarks"],
        "key_claims": [],
    }


def _review_section_payload() -> dict:
    return {
        "title": SECTION_TITLE,
        "theme_id": THEME_ID,
        "label": THEME_NAME,
        "content": "Section body text.",
    }


@pytest.fixture()
def store() -> PapersStore:
    """Create a PapersStore with mocked dependencies."""
    with (
        patch(
            "papers_mcp.store.QdrantClient",
        ) as mock_client_cls,
        patch(
            "papers_mcp.store.GeminiEmbedder",
        ) as mock_embedder_cls,
    ):
        mock_client = MagicMock()
        mock_embedder = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_embedder_cls.return_value = mock_embedder
        s = PapersStore()
    # Expose mocks for per-test configuration
    s._test_client = mock_client  # type: ignore[attr-defined]
    s._test_embedder = mock_embedder  # type: ignore[attr-defined]
    return s


# --------------- _scroll helper ---------------


class TestScroll:
    """Tests for the _scroll helper method."""

    def test_returns_payloads(self, store: PapersStore) -> None:
        """Happy path: payloads are extracted from records."""
        # Arrange
        payload = _theme_payload()
        store._test_client.scroll.return_value = (  # type: ignore[attr-defined]
            [_make_record(payload)],
            None,
        )

        # Act
        result = store._scroll("paper_themes")

        # Assert
        assert result == [payload]

    def test_skips_none_payloads(
        self,
        store: PapersStore,
    ) -> None:
        """Records with None payload are filtered out."""
        # Arrange
        store._test_client.scroll.return_value = (  # type: ignore[attr-defined]
            [
                _make_record(_theme_payload()),
                SimpleNamespace(payload=None),
            ],
            None,
        )

        # Act
        result = store._scroll("paper_themes")

        # Assert
        assert len(result) == 1

    def test_empty_collection(self, store: PapersStore) -> None:
        """Empty collection returns empty list."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]

        # Act
        result = store._scroll("paper_themes")

        # Assert
        assert result == []

    def test_exception_returns_empty(
        self,
        store: PapersStore,
    ) -> None:
        """Qdrant errors are caught; empty list returned."""
        # Arrange
        store._test_client.scroll.side_effect = RuntimeError(  # type: ignore[attr-defined]
            "connection lost",
        )

        # Act
        result = store._scroll("paper_themes")

        # Assert
        assert result == []

    def test_passes_filter_and_limit(
        self,
        store: PapersStore,
    ) -> None:
        """Filter and limit are forwarded to the client."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]
        custom_limit = 5

        # Act
        store._scroll(
            "paper_themes",
            scroll_filter="fake_filter",  # type: ignore[arg-type]
            limit=custom_limit,
        )

        # Assert
        store._test_client.scroll.assert_called_once_with(  # type: ignore[attr-defined]
            collection_name="paper_themes",
            scroll_filter="fake_filter",
            limit=custom_limit,
            with_payload=True,
            with_vectors=False,
        )

    def test_default_limit(self, store: PapersStore) -> None:
        """Default limit matches module constant."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]

        # Act
        store._scroll("paper_themes")

        # Assert
        call_kwargs = store._test_client.scroll.call_args  # type: ignore[attr-defined]
        assert call_kwargs.kwargs["limit"] == _SCROLL_LIMIT


# --------------- get_paper_themes ---------------


class TestGetPaperThemes:
    """Tests for get_paper_themes."""

    def test_happy_path(self, store: PapersStore) -> None:
        """Returns validated ThemeResult list."""
        # Arrange
        store._test_client.scroll.return_value = (  # type: ignore[attr-defined]
            [_make_record(_theme_payload())],
            None,
        )

        # Act
        result = store.get_paper_themes(PAPER_ID)

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], ThemeResult)
        assert result[0].name == THEME_NAME

    def test_empty_result(self, store: PapersStore) -> None:
        """No themes returns empty list."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]

        # Act
        result = store.get_paper_themes(PAPER_ID)

        # Assert
        assert result == []

    def test_multiple_themes(self, store: PapersStore) -> None:
        """Multiple themes are returned."""
        # Arrange
        records = [
            _make_record(_theme_payload(name="Theme A")),
            _make_record(_theme_payload(name="Theme B")),
        ]
        store._test_client.scroll.return_value = (records, None)  # type: ignore[attr-defined]

        # Act
        result = store.get_paper_themes(PAPER_ID)

        # Assert
        assert len(result) == 2
        names = {t.name for t in result}
        assert names == {"Theme A", "Theme B"}


# --------------- get_claims_by_theme ---------------


class TestGetClaimsByTheme:
    """Tests for get_claims_by_theme."""

    def test_happy_path(self, store: PapersStore) -> None:
        """Returns validated ClaimResult list."""
        # Arrange
        store._test_client.scroll.return_value = (  # type: ignore[attr-defined]
            [_make_record(_claim_payload())],
            None,
        )

        # Act
        result = store.get_claims_by_theme(THEME_NAME)

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], ClaimResult)
        assert result[0].text == CLAIM_TEXT

    def test_empty(self, store: PapersStore) -> None:
        """No claims returns empty list."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]

        # Act
        result = store.get_claims_by_theme(THEME_NAME)

        # Assert
        assert result == []


# --------------- get_theme_map ---------------


class TestGetThemeMap:
    """Tests for get_theme_map."""

    def test_happy_path(self, store: PapersStore) -> None:
        """Returns validated ThemeMapEntry list."""
        # Arrange
        store._test_client.scroll.return_value = (  # type: ignore[attr-defined]
            [_make_record(_theme_map_payload())],
            None,
        )

        # Act
        result = store.get_theme_map()

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], ThemeMapEntry)
        assert result[0].aliases == ["Attn"]

    def test_empty(self, store: PapersStore) -> None:
        """Empty theme map returns empty list."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]

        # Act
        result = store.get_theme_map()

        # Assert
        assert result == []


# --------------- get_theme_review ---------------


class TestGetThemeReview:
    """Tests for get_theme_review."""

    def test_happy_path(self, store: PapersStore) -> None:
        """Returns ThemeReviewResult when found."""
        # Arrange
        store._test_client.scroll.return_value = (  # type: ignore[attr-defined]
            [_make_record(_theme_review_payload())],
            None,
        )

        # Act
        result = store.get_theme_review(THEME_NAME)

        # Assert
        assert result is not None
        assert isinstance(result, ThemeReviewResult)
        assert result.review == REVIEW_TEXT

    def test_not_found(self, store: PapersStore) -> None:
        """Returns None when no review exists."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]

        # Act
        result = store.get_theme_review("Nonexistent")

        # Assert
        assert result is None

    def test_uses_limit_one(self, store: PapersStore) -> None:
        """Scroll is called with limit=1."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]

        # Act
        store.get_theme_review(THEME_NAME)

        # Assert
        call_kwargs = store._test_client.scroll.call_args  # type: ignore[attr-defined]
        assert call_kwargs.kwargs["limit"] == 1


# --------------- get_literature_review ---------------


class TestGetLiteratureReview:
    """Tests for get_literature_review."""

    def test_happy_path(self, store: PapersStore) -> None:
        """Returns ReviewSection list."""
        # Arrange
        store._test_client.scroll.return_value = (  # type: ignore[attr-defined]
            [_make_record(_review_section_payload())],
            None,
        )

        # Act
        result = store.get_literature_review()

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], ReviewSection)
        assert result[0].title == SECTION_TITLE

    def test_empty(self, store: PapersStore) -> None:
        """Empty review returns empty list."""
        # Arrange
        store._test_client.scroll.return_value = ([], None)  # type: ignore[attr-defined]

        # Act
        result = store.get_literature_review()

        # Assert
        assert result == []


# --------------- search_claims ---------------


class TestSearchClaims:
    """Tests for search_claims (vector search)."""

    def _setup_search(
        self,
        store: PapersStore,
        points: list | None = None,
    ) -> None:
        """Configure mock for query_points."""
        if points is None:
            points = []
        response = SimpleNamespace(points=points)
        store._test_client.query_points.return_value = response  # type: ignore[attr-defined]
        store._test_embedder.get_embedding.return_value = FAKE_EMBEDDING  # type: ignore[attr-defined]

    def test_happy_path(self, store: PapersStore) -> None:
        """Returns ClaimSearchResult with score."""
        # Arrange
        point = SimpleNamespace(
            payload=_claim_payload(),
            score=SCORE_HIGH,
        )
        self._setup_search(store, [point])

        # Act
        result = store.search_claims("attention query")

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], ClaimSearchResult)
        assert result[0].score == SCORE_HIGH
        assert result[0].claim.text == CLAIM_TEXT

    def test_empty_results(self, store: PapersStore) -> None:
        """No matching claims returns empty list."""
        # Arrange
        self._setup_search(store, [])

        # Act
        result = store.search_claims("obscure query")

        # Assert
        assert result == []

    def test_custom_limit(self, store: PapersStore) -> None:
        """Custom limit is forwarded to query_points."""
        # Arrange
        self._setup_search(store, [])
        custom_limit = 5

        # Act
        store.search_claims("query", limit=custom_limit)

        # Assert
        call_kwargs = store._test_client.query_points.call_args  # type: ignore[attr-defined]
        assert call_kwargs.kwargs["limit"] == custom_limit

    def test_default_limit_from_settings(
        self,
        store: PapersStore,
    ) -> None:
        """None limit falls back to settings.default_top_k."""
        # Arrange
        self._setup_search(store, [])

        # Act
        store.search_claims("query", limit=None)

        # Assert
        call_kwargs = store._test_client.query_points.call_args  # type: ignore[attr-defined]
        assert call_kwargs.kwargs["limit"] == DEFAULT_TOP_K

    def test_exception_returns_empty(
        self,
        store: PapersStore,
    ) -> None:
        """Qdrant query error returns empty list."""
        # Arrange
        store._test_embedder.get_embedding.return_value = (  # type: ignore[attr-defined]
            FAKE_EMBEDDING
        )
        store._test_client.query_points.side_effect = (  # type: ignore[attr-defined]
            RuntimeError("timeout")
        )

        # Act
        result = store.search_claims("query")

        # Assert
        assert result == []

    def test_multiple_results_ordered(
        self,
        store: PapersStore,
    ) -> None:
        """Multiple points are returned in order."""
        # Arrange
        high_score = 0.95
        low_score = 0.70
        points = [
            SimpleNamespace(
                payload=_claim_payload(text="First"),
                score=high_score,
            ),
            SimpleNamespace(
                payload=_claim_payload(text="Second"),
                score=low_score,
            ),
        ]
        self._setup_search(store, points)

        # Act
        result = store.search_claims("query")

        # Assert
        assert len(result) == 2
        assert result[0].score == high_score
        assert result[1].score == low_score

    def test_point_with_empty_payload(
        self,
        store: PapersStore,
    ) -> None:
        """Point with None payload uses empty dict fallback."""
        # Arrange
        point = SimpleNamespace(
            payload=None,
            score=SCORE_HIGH,
        )
        self._setup_search(store, [point])

        # Act / Assert — validation will fail on missing fields
        with pytest.raises(Exception):
            store.search_claims("query")


# --------------- health ---------------


class TestHealth:
    """Tests for health() method."""

    def test_all_collections_healthy(
        self,
        store: PapersStore,
    ) -> None:
        """All collections report points and status."""
        # Arrange
        points_count = 42
        info = SimpleNamespace(
            points_count=points_count,
            status=SimpleNamespace(value="green"),
        )
        store._test_client.get_collection.return_value = info  # type: ignore[attr-defined]

        # Act
        result = store.health()

        # Assert
        expected_count = 5  # number of collections
        assert len(result) == expected_count
        for name, data in result.items():
            assert data["points"] == points_count
            assert data["status"] == "green"

    def test_missing_collection(
        self,
        store: PapersStore,
    ) -> None:
        """Missing collection gets not_found status."""
        # Arrange
        store._test_client.get_collection.side_effect = (  # type: ignore[attr-defined]
            RuntimeError("not found")
        )

        # Act
        result = store.health()

        # Assert
        expected_count = 5
        assert len(result) == expected_count
        for data in result.values():
            assert data["status"] == "not_found"
            assert data["points"] == 0

    def test_partial_failure(
        self,
        store: PapersStore,
    ) -> None:
        """Some collections healthy, some missing."""
        # Arrange
        healthy_info = SimpleNamespace(
            points_count=10,
            status=SimpleNamespace(value="green"),
        )
        call_count = 0

        def side_effect(name: str) -> SimpleNamespace:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return healthy_info
            raise RuntimeError("not found")

        store._test_client.get_collection.side_effect = (  # type: ignore[attr-defined]
            side_effect
        )

        # Act
        result = store.health()

        # Assert
        statuses = [d["status"] for d in result.values()]
        assert "green" in statuses
        assert "not_found" in statuses


# --------------- get_store singleton ---------------


class TestGetStore:
    """Tests for get_store() singleton function."""

    def test_returns_papers_store(self) -> None:
        """get_store returns a PapersStore instance."""
        # Arrange / Act
        with (
            patch("papers_mcp.store.QdrantClient"),
            patch("papers_mcp.store.GeminiEmbedder"),
        ):
            import papers_mcp.store as store_mod

            store_mod._store = None
            result = get_store()

        # Assert
        assert isinstance(result, PapersStore)

    def test_singleton_behavior(self) -> None:
        """Subsequent calls return the same instance."""
        # Arrange
        with (
            patch("papers_mcp.store.QdrantClient"),
            patch("papers_mcp.store.GeminiEmbedder"),
        ):
            import papers_mcp.store as store_mod

            store_mod._store = None

            # Act
            first = get_store()
            second = get_store()

        # Assert
        assert first is second

    def test_reset_creates_new(self) -> None:
        """Resetting _store to None creates a new instance."""
        # Arrange
        with (
            patch("papers_mcp.store.QdrantClient"),
            patch("papers_mcp.store.GeminiEmbedder"),
        ):
            import papers_mcp.store as store_mod

            store_mod._store = None
            first = get_store()

            # Act
            store_mod._store = None
            second = get_store()

        # Assert
        assert first is not second
