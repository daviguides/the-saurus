"""Tests for PDF ingestion: extraction, fallback, quality, metadata."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from pipeline.ingestion import IngestedPaper, IngestionError, ingest_pdf
from pipeline.ingestion.extract import (
    QUALITY_THRESHOLD,
    _check_quality,
    _scrub_pii,
    extract_pdfplumber,
    extract_pymupdf,
)
from pipeline.ingestion.models import Paragraph as IngParagraph


def _make_pdf(pages_content: list[list[tuple[str, str]]], page_count: int | None = None) -> bytes:
    """Generate a PDF from structured content.

    Args:
        pages_content: List of pages, each page is a list of (style_name, text) tuples.
            style names: "title", "author", "heading", "body"
        page_count: If set and > len(pages_content), add blank pages to reach count.
    """
    from io import BytesIO

    styles = getSampleStyleSheet()
    style_map = {
        "title": ParagraphStyle("T", parent=styles["Title"], fontSize=18, spaceAfter=12),
        "author": ParagraphStyle(
            "A", parent=styles["Normal"], fontSize=12, spaceAfter=24, alignment=1
        ),
        "heading": ParagraphStyle("H", parent=styles["Heading2"], fontSize=14, spaceAfter=8),
        "body": ParagraphStyle("B", parent=styles["Normal"], fontSize=10, spaceAfter=8, leading=14),
    }

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    story = []

    for i, page in enumerate(pages_content):
        if i > 0:
            story.append(PageBreak())
        for style_name, text in page:
            story.append(Paragraph(text, style_map[style_name]))
            if style_name == "title":
                story.append(Spacer(1, 6))

    # Pad with blank pages if needed
    target = page_count or len(pages_content)
    for _ in range(target - len(pages_content)):
        story.append(PageBreak())
        story.append(Paragraph("&nbsp;", style_map["body"]))

    doc.build(story)
    return buf.getvalue()


@pytest.fixture
def sample_pdf() -> bytes:
    """Two-page scientific paper PDF."""
    return _make_pdf([
        [
            ("title", "A Survey of Neural Architecture Search Methods"),
            ("author", "Jane Smith, John Doe, Alice Johnson"),
            ("heading", "Abstract"),
            ("body", "Neural Architecture Search has emerged as a promising approach."),
            ("heading", "1. Introduction"),
            ("body", "The design of neural networks has traditionally been manual."),
        ],
        [
            ("heading", "2. Methods"),
            ("body", "Search strategies define how the search space is explored."),
            ("body", "Evolutionary methods maintain a population of architectures."),
            ("heading", "3. Results"),
            ("body", "We evaluated all methods on standard benchmarks."),
        ],
    ])


@pytest.fixture
def multipage_pdf() -> bytes:
    """10-page PDF for multipage handling test."""
    pages = []
    pages.append([
        ("title", "A Comprehensive Review of Machine Learning"),
        ("author", "Alice Smith; Bob Jones; Carol White"),
        ("heading", "Abstract"),
        ("body", "This paper reviews recent advances in machine learning methods."),
    ])
    for i in range(2, 11):
        pages.append([
            ("heading", f"{i}. Section {i}"),
            ("body", f"Content for section {i} with enough text to pass quality threshold. " * 3),
        ])
    return _make_pdf(pages)


class TestExtractPymupdf:
    def test_basic_extraction(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)

        assert result.page_count == 2
        assert len(result.paragraphs) > 0
        assert all(isinstance(p, IngParagraph) for p in result.paragraphs)

    def test_paragraphs_have_metadata(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)

        for p in result.paragraphs:
            assert p.page >= 1
            assert p.index >= 1
            assert len(p.text) > 0

    def test_page_numbers_correct(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)

        page1_paras = [p for p in result.paragraphs if p.page == 1]
        page2_paras = [p for p in result.paragraphs if p.page == 2]
        assert len(page1_paras) > 0
        assert len(page2_paras) > 0

    def test_heading_detection(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)

        headings = [p for p in result.paragraphs if p.is_heading]
        assert len(headings) >= 3  # title + Abstract + 1. Introduction at minimum

        # Title should be heading level 1
        title_paras = [p for p in headings if p.heading_level == 1]
        assert len(title_paras) >= 1

        # Section headings should be level 2
        section_headings = [p for p in headings if p.heading_level == 2]
        assert len(section_headings) >= 2


class TestExtractPdfplumber:
    def test_basic_extraction(self, sample_pdf: bytes) -> None:
        result = extract_pdfplumber(sample_pdf)

        assert result.page_count == 2
        assert len(result.paragraphs) > 0

    def test_paragraphs_have_metadata(self, sample_pdf: bytes) -> None:
        result = extract_pdfplumber(sample_pdf)

        for p in result.paragraphs:
            assert p.page >= 1
            assert p.index >= 1
            assert len(p.text) > 0


class TestTitleDetection:
    def test_pymupdf_title(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)
        assert "Neural Architecture Search" in result.title

    def test_pdfplumber_title(self, sample_pdf: bytes) -> None:
        result = extract_pdfplumber(sample_pdf)
        assert "Neural Architecture Search" in result.title


class TestAuthorDetection:
    def test_pymupdf_authors_comma(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)
        assert len(result.authors) == 3
        assert "Jane Smith" in result.authors

    def test_pdfplumber_authors_comma(self, sample_pdf: bytes) -> None:
        result = extract_pdfplumber(sample_pdf)
        assert len(result.authors) == 3
        assert "Jane Smith" in result.authors

    def test_semicolon_authors(self, multipage_pdf: bytes) -> None:
        result = extract_pymupdf(multipage_pdf)
        assert len(result.authors) == 3
        assert "Alice Smith" in result.authors


class TestToMarkdown:
    def test_renders_headings(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)
        md = result.to_markdown()

        assert md.startswith("# ")
        assert "## " in md

    def test_contains_body_text(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)
        md = result.to_markdown()

        assert "promising approach" in md

    def test_paragraphs_separated(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)
        md = result.to_markdown()

        # Each paragraph followed by blank line
        lines = md.split("\n")
        non_empty_indices = [i for i, l in enumerate(lines) if l.strip()]
        for i in range(len(non_empty_indices) - 1):
            # At least one blank line between non-empty lines
            assert non_empty_indices[i + 1] - non_empty_indices[i] >= 2


class TestToAnnotatedMarkdown:
    """Regression coverage for render_annotated_markdown extraction (models.py)."""

    def test_renders_headings(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)
        md = result.to_annotated_markdown()

        assert md.startswith("# ")
        assert "## " in md

    def test_contains_position_tags(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)
        md = result.to_annotated_markdown()

        assert "[p.1,§" in md

    def test_contains_body_text(self, sample_pdf: bytes) -> None:
        result = extract_pymupdf(sample_pdf)
        md = result.to_annotated_markdown()

        assert "promising approach" in md


class TestIngestPdf:
    def test_uses_pymupdf_when_quality_good(self, sample_pdf: bytes) -> None:
        result = ingest_pdf(sample_pdf)

        assert result.page_count == 2
        assert len(result.paragraphs) > 0
        assert "Neural Architecture Search" in result.title

    def test_fallback_on_pymupdf_exception(self, sample_pdf: bytes) -> None:
        with patch(
            "pipeline.ingestion.extract.extract_pymupdf", side_effect=RuntimeError("broken")
        ):
            result = ingest_pdf(sample_pdf)

        assert result.page_count == 2
        assert len(result.paragraphs) > 0

    def test_fallback_on_low_quality(self, sample_pdf: bytes) -> None:
        low_quality = IngestedPaper(title="", authors=[], page_count=2, paragraphs=[])

        with patch("pipeline.ingestion.extract.extract_pymupdf", return_value=low_quality):
            result = ingest_pdf(sample_pdf)

        assert len(result.paragraphs) > 0

    def test_raises_when_both_fail(self) -> None:
        with (
            patch(
                "pipeline.ingestion.extract.extract_pymupdf", side_effect=RuntimeError("fail1")
            ),
            patch(
                "pipeline.ingestion.extract.extract_pdfplumber", side_effect=RuntimeError("fail2")
            ),
        ):
            with pytest.raises(IngestionError):
                ingest_pdf(b"fake pdf bytes")


class TestMultipage:
    def test_handles_10_pages(self, multipage_pdf: bytes) -> None:
        result = ingest_pdf(multipage_pdf)

        assert result.page_count == 10
        assert len(result.paragraphs) > 10

        # Paragraph indices reset per page
        page1_paras = [p for p in result.paragraphs if p.page == 1]
        page2_paras = [p for p in result.paragraphs if p.page == 2]
        assert page1_paras[0].index == 1
        assert page2_paras[0].index == 1


class TestQualityCheck:
    def test_good_quality(self) -> None:
        paper = IngestedPaper(
            title="Test",
            page_count=2,
            paragraphs=[IngParagraph(page=1, index=1, text="x" * 200)],
        )
        assert _check_quality(paper) is True

    def test_low_quality(self) -> None:
        paper = IngestedPaper(
            title="Test",
            page_count=10,
            paragraphs=[IngParagraph(page=1, index=1, text="short")],
        )
        assert _check_quality(paper) is False

    def test_zero_pages(self) -> None:
        paper = IngestedPaper(title="Test", page_count=0, paragraphs=[])
        assert _check_quality(paper) is False


@pytest.fixture
def pii_pdf() -> bytes:
    """Paper with author block plus an email, a phone number, and a city name in body text."""
    return _make_pdf([
        [
            ("title", "A Survey of Neural Architecture Search Methods"),
            ("author", "Jane Rodriguez, John Doe"),
            ("heading", "Abstract"),
            ("body", "Neural Architecture Search has emerged as a promising approach."),
            ("heading", "Correspondence"),
            (
                "body",
                "Contact the corresponding author at j.rodriguez@example.edu or call "
                "555-123-4567. The lab is based in Palo Alto.",
            ),
        ],
    ])


class TestPiiScrub:
    def test_email_redacted(self, pii_pdf: bytes) -> None:
        result = ingest_pdf(pii_pdf)
        body = " ".join(p.text for p in result.paragraphs)
        assert "j.rodriguez@example.edu" not in body
        assert "[EMAIL]" in body

    def test_phone_redacted(self, pii_pdf: bytes) -> None:
        result = ingest_pdf(pii_pdf)
        body = " ".join(p.text for p in result.paragraphs)
        assert "555-123-4567" not in body
        assert "[PHONE]" in body

    def test_location_redacted(self, pii_pdf: bytes) -> None:
        result = ingest_pdf(pii_pdf)
        body = " ".join(p.text for p in result.paragraphs)
        assert "Palo Alto" not in body
        assert "[LOCATION]" in body

    def test_author_names_preserved(self, pii_pdf: bytes) -> None:
        result = ingest_pdf(pii_pdf)
        assert "Jane Rodriguez" in result.authors
        assert "John Doe" in result.authors

    def test_paragraph_count_unchanged(self, pii_pdf: bytes) -> None:
        result = ingest_pdf(pii_pdf)
        raw_count = len(extract_pymupdf(pii_pdf).paragraphs)
        assert len(result.paragraphs) == raw_count

    def test_non_pii_paragraph_unchanged(self, pii_pdf: bytes) -> None:
        result = ingest_pdf(pii_pdf)
        abstract = next(p for p in result.paragraphs if "promising approach" in p.text)
        assert abstract.text == "Neural Architecture Search has emerged as a promising approach."

    def test_redaction_logged_without_pii_value(
        self, pii_pdf: bytes, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("INFO", logger="pipeline.ingestion.extract"):
            ingest_pdf(pii_pdf)

        redaction_logs = [r for r in caplog.records if "PII redacted" in r.message]
        assert len(redaction_logs) >= 3  # email + phone + location
        for record in redaction_logs:
            assert "j.rodriguez@example.edu" not in record.message
            assert "555-123-4567" not in record.message
            assert "Palo Alto" not in record.message
            assert "page=" in record.message
            assert "paragraph=" in record.message

    def test_scrub_pii_passes_through_clean_paragraphs(self) -> None:
        clean = [IngParagraph(page=1, index=1, text="Deep learning improves accuracy.")]
        scrubbed = _scrub_pii(clean)
        assert scrubbed[0].text == clean[0].text
