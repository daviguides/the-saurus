"""Tests for two-tier chunking: heading-aware structural + embedding-similarity."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pipeline.ingestion.chunking import chunk_by_heading, chunk_by_similarity, chunk_paper
from pipeline.ingestion.models import Paragraph

# --- Helpers ---


def _p(
    text: str,
    *,
    page: int = 1,
    index: int = 1,
    is_heading: bool = False,
    heading_level: int = 0,
) -> Paragraph:
    """Build a Paragraph with sane defaults."""
    return Paragraph(
        page=page,
        index=index,
        text=text,
        is_heading=is_heading,
        heading_level=heading_level,
    )


# --- chunk_by_heading ---


class TestChunkByHeading:
    def test_empty_input_returns_empty_list(self) -> None:
        assert chunk_by_heading([]) == []

    def test_splits_at_section_headings(self) -> None:
        paragraphs = [
            _p("Title", index=1, is_heading=True, heading_level=1),
            _p("Introduction", index=2, is_heading=True, heading_level=2),
            _p("Intro body.", index=3),
            _p("Methods", index=4, is_heading=True, heading_level=2),
            _p("Methods body.", index=5),
        ]

        chunks = chunk_by_heading(paragraphs)

        assert len(chunks) == 2
        assert [p.text for p in chunks[0]] == ["Title", "Introduction", "Intro body."]
        assert [p.text for p in chunks[1]] == ["Methods", "Methods body."]

    def test_front_matter_merges_into_first_section_chunk(self) -> None:
        """Front matter (before the first section heading) has no section of its
        own — it would almost certainly yield zero themes — so it merges into
        the first section's chunk rather than becoming its own chunk."""
        paragraphs = [
            _p("Title", index=1, is_heading=True, heading_level=1),
            _p("Authors", index=2),
            _p("Abstract text with no heading.", index=3),
            _p("Introduction", index=4, is_heading=True, heading_level=2),
            _p("Intro body.", index=5),
            _p("Methods", index=6, is_heading=True, heading_level=2),
            _p("Methods body.", index=7),
        ]

        chunks = chunk_by_heading(paragraphs)

        assert len(chunks) == 2
        assert [p.text for p in chunks[0]] == [
            "Title",
            "Authors",
            "Abstract text with no heading.",
            "Introduction",
            "Intro body.",
        ]
        assert [p.text for p in chunks[1]] == ["Methods", "Methods body."]

    def test_no_headings_returns_single_chunk(self) -> None:
        paragraphs = [_p("Body 1", index=1), _p("Body 2", index=2), _p("Body 3", index=3)]

        chunks = chunk_by_heading(paragraphs)

        assert len(chunks) == 1
        assert chunks[0] == paragraphs

    def test_title_only_no_section_headings_returns_single_chunk(self) -> None:
        paragraphs = [
            _p("Title", index=1, is_heading=True, heading_level=1),
            _p("Body.", index=2),
        ]

        chunks = chunk_by_heading(paragraphs)

        assert len(chunks) == 1
        assert [p.text for p in chunks[0]] == ["Title", "Body."]

    def test_paragraph_order_preserved_within_chunk(self) -> None:
        paragraphs = [
            _p("Section", index=1, is_heading=True, heading_level=2),
            _p("First.", index=2),
            _p("Second.", index=3),
            _p("Third.", index=4),
        ]

        chunks = chunk_by_heading(paragraphs)

        assert [p.text for p in chunks[0]] == ["Section", "First.", "Second.", "Third."]

    def test_three_sections_produce_three_chunks(self) -> None:
        paragraphs = [
            _p("Intro", index=1, is_heading=True, heading_level=2),
            _p("Methods", index=2, is_heading=True, heading_level=2),
            _p("Results", index=3, is_heading=True, heading_level=2),
        ]

        chunks = chunk_by_heading(paragraphs)

        assert len(chunks) == 3


# --- chunk_by_similarity ---


class TestChunkBySimilarity:
    async def test_empty_input_returns_empty_list(self) -> None:
        assert await chunk_by_similarity([]) == []

    async def test_single_paragraph_returns_single_chunk(self) -> None:
        paragraphs = [_p("Only paragraph.", index=1)]

        chunks = await chunk_by_similarity(paragraphs)

        assert chunks == [paragraphs]

    async def test_splits_where_similarity_drops_below_threshold(self) -> None:
        paragraphs = [
            _p("First.", index=1),
            _p("Similar to first.", index=2),
            _p("Unrelated topic.", index=3),
        ]
        # p0/p1 identical direction (cos=1.0, stays together);
        # p1/p2 orthogonal (cos=0.0, below default threshold 0.55 → split)
        vectors = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

        with patch("pipeline.ingestion.chunking.embed_batch", AsyncMock(return_value=vectors)):
            chunks = await chunk_by_similarity(paragraphs)

        assert [p.text for p in chunks[0]] == ["First.", "Similar to first."]
        assert [p.text for p in chunks[1]] == ["Unrelated topic."]

    async def test_threshold_override_forces_no_split(self) -> None:
        paragraphs = [_p("A", index=1), _p("B", index=2)]
        vectors = [[1.0, 0.0], [0.0, 1.0]]  # orthogonal, cos=0.0

        with patch("pipeline.ingestion.chunking.embed_batch", AsyncMock(return_value=vectors)):
            chunks = await chunk_by_similarity(paragraphs, threshold=-1.0)

        assert len(chunks) == 1

    async def test_threshold_override_forces_split_every_pair(self) -> None:
        paragraphs = [_p("A", index=1), _p("B", index=2)]
        vectors = [[1.0, 0.0], [1.0, 0.0]]  # identical, cos=1.0

        with patch("pipeline.ingestion.chunking.embed_batch", AsyncMock(return_value=vectors)):
            chunks = await chunk_by_similarity(paragraphs, threshold=2.0)

        assert len(chunks) == 2


# --- chunk_paper (dispatch) ---


class TestChunkPaper:
    async def test_empty_input_returns_empty_list(self) -> None:
        assert await chunk_paper([]) == []

    async def test_well_structured_input_stays_on_tier_1(self) -> None:
        paragraphs = [
            _p("Introduction", index=1, is_heading=True, heading_level=2),
            _p("Intro body.", index=2),
            _p("Methods", index=3, is_heading=True, heading_level=2),
            _p("Methods body.", index=4),
        ]
        mock_embed_batch = AsyncMock()

        with patch("pipeline.ingestion.chunking.embed_batch", mock_embed_batch):
            chunks = await chunk_paper(paragraphs)

        assert len(chunks) == 2
        mock_embed_batch.assert_not_called()

    async def test_sparse_heading_input_falls_back_to_tier_2(self) -> None:
        paragraphs = [
            _p("First.", index=1),
            _p("Similar to first.", index=2),
            _p("Unrelated topic.", index=3),
        ]
        vectors = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

        with patch("pipeline.ingestion.chunking.embed_batch", AsyncMock(return_value=vectors)):
            chunks = await chunk_paper(paragraphs)

        assert [p.text for p in chunks[0]] == ["First.", "Similar to first."]
        assert [p.text for p in chunks[1]] == ["Unrelated topic."]
