"""Tests for Tier 1 heading-aware structural chunking."""

from __future__ import annotations

from pipeline.ingestion.chunking import chunk_by_heading
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
