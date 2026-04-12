"""PDF extraction: pymupdf primary, pdfplumber fallback."""

from __future__ import annotations

import logging
import re
from io import BytesIO
from statistics import median

from .models import IngestedPaper, Paragraph

logger = logging.getLogger(__name__)

QUALITY_THRESHOLD = 50  # minimum chars per page to consider extraction successful

# PDF ligatures and common unicode artifacts → ASCII equivalents
_LIGATURE_MAP = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "ft",
    "\ufb06": "st",
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2013": "-",   # en dash
    "\u2014": "--",  # em dash
    "\u2026": "...", # ellipsis
    "\u00a0": " ",   # non-breaking space
    "\u200b": "",    # zero-width space
    "\u200c": "",    # zero-width non-joiner
    "\u200d": "",    # zero-width joiner
    "\ufeff": "",    # BOM
}

_LIGATURE_PATTERN = re.compile("|".join(re.escape(k) for k in _LIGATURE_MAP))


def _normalize_text(text: str) -> str:
    """Clean PDF text artifacts: ligatures, smart quotes, invisible chars."""
    return _LIGATURE_PATTERN.sub(lambda m: _LIGATURE_MAP[m.group()], text)


from pipeline.core.exceptions import IngestionError  # noqa: E402

# Re-export for backward compatibility
__all__ = ["IngestionError", "ingest_pdf", "extract_pymupdf", "extract_pdfplumber"]


def _parse_authors(text: str) -> list[str]:
    """Split an author line into individual names."""
    # Try semicolons first, then commas
    if ";" in text:
        authors = [a.strip() for a in text.split(";")]
    else:
        authors = [a.strip() for a in text.split(",")]
    return [a for a in authors if a]


def extract_pymupdf(pdf_bytes: bytes) -> IngestedPaper:
    """Extract paragraphs from PDF using pymupdf (fitz). Primary extractor."""
    import fitz

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page_count = len(doc)
        paragraphs: list[Paragraph] = []

        # First pass: collect all body font sizes to determine median
        body_sizes: list[float] = []
        for page in doc:
            d = page.get_text("dict")
            for block in d["blocks"]:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        if "Bold" not in span["font"] and span["text"].strip():
                            body_sizes.append(span["size"])

        median_body_size = median(body_sizes) if body_sizes else 10.0
        heading_threshold = median_body_size + 1.0

        # Second pass: extract paragraphs
        title = ""
        authors: list[str] = []
        max_font_size_page1 = 0.0
        title_block_idx: int | None = None

        for page_idx, page in enumerate(doc):
            d = page.get_text("dict")
            para_idx = 0

            for block_idx, block in enumerate(d["blocks"]):
                if block["type"] != 0:
                    continue

                # Collect block text and font info
                block_text_parts: list[str] = []
                block_max_size = 0.0
                has_bold = False

                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += _normalize_text(span["text"])
                        block_max_size = max(block_max_size, span["size"])
                        if "Bold" in span["font"]:
                            has_bold = True
                    block_text_parts.append(line_text)

                block_text = "\n".join(block_text_parts).strip()
                if not block_text:
                    continue

                para_idx += 1
                is_heading = has_bold and block_max_size > heading_threshold
                heading_level = 0

                # Title detection: largest font on page 1
                if page_idx == 0:
                    if block_max_size > max_font_size_page1:
                        max_font_size_page1 = block_max_size
                        title = block_text.replace("\n", " ")
                        title_block_idx = block_idx
                        is_heading = True
                        heading_level = 1
                    elif (
                        not authors
                        and title_block_idx is not None
                        and block_idx > title_block_idx
                        and not is_heading
                    ):
                        # First non-heading block after title = authors
                        authors = _parse_authors(block_text.replace("\n", " "))

                if is_heading and heading_level == 0:
                    heading_level = 2

                paragraphs.append(
                    Paragraph(
                        page=page_idx + 1,
                        index=para_idx,
                        text=block_text.replace("\n", " "),
                        is_heading=is_heading,
                        heading_level=heading_level,
                    )
                )

    return IngestedPaper(
        title=title,
        authors=authors,
        page_count=page_count,
        paragraphs=paragraphs,
    )


def extract_pdfplumber(pdf_bytes: bytes) -> IngestedPaper:
    """Extract paragraphs from PDF using pdfplumber. Fallback extractor."""
    import pdfplumber

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        page_count = len(pdf.pages)
        paragraphs: list[Paragraph] = []

        # Collect body sizes across all pages for threshold
        body_sizes: list[float] = []
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["fontname", "size"])
            for w in words:
                if "Bold" not in w.get("fontname", ""):
                    body_sizes.append(w.get("size", 10.0))

        median_body_size = median(body_sizes) if body_sizes else 10.0
        heading_threshold = median_body_size + 1.0
        line_height = median_body_size * 1.4  # approximate leading

        title = ""
        authors: list[str] = []
        max_font_size_page1 = 0.0
        title_found = False

        for page_idx, page in enumerate(pdf.pages):
            words = page.extract_words(extra_attrs=["fontname", "size"])
            if not words:
                continue

            # Group words into lines by top coordinate
            line_groups: dict[int, list[dict]] = {}
            for w in words:
                key = round(w["top"])
                if key not in line_groups:
                    line_groups[key] = []
                line_groups[key].append(w)

            sorted_tops = sorted(line_groups.keys())

            # Merge lines into paragraphs by y-gap
            current_para_words: list[dict] = []
            current_para_lines: list[str] = []
            para_idx = 0

            def _flush_paragraph() -> None:
                nonlocal para_idx, title, authors, max_font_size_page1, title_found
                if not current_para_lines:
                    return

                text = _normalize_text(" ".join(current_para_lines).strip())
                if not text:
                    return

                para_idx += 1

                # Font analysis from words in this paragraph
                para_max_size = max((w.get("size", 10.0) for w in current_para_words), default=10.0)
                para_has_bold = any("Bold" in w.get("fontname", "") for w in current_para_words)
                is_heading = para_has_bold and para_max_size > heading_threshold
                heading_level = 0

                if page_idx == 0:
                    if para_max_size > max_font_size_page1:
                        max_font_size_page1 = para_max_size
                        title = text
                        title_found = True
                        is_heading = True
                        heading_level = 1
                    elif not authors and title_found and not is_heading:
                        authors = _parse_authors(text)

                if is_heading and heading_level == 0:
                    heading_level = 2

                paragraphs.append(
                    Paragraph(
                        page=page_idx + 1,
                        index=para_idx,
                        text=text,
                        is_heading=is_heading,
                        heading_level=heading_level,
                    )
                )

            prev_top: int | None = None
            for top in sorted_tops:
                gap = (top - prev_top) if prev_top is not None else 0

                if prev_top is not None and gap > line_height * 1.5:
                    _flush_paragraph()
                    current_para_words = []
                    current_para_lines = []

                line_words = sorted(line_groups[top], key=lambda w: w["x0"])
                current_para_lines.append(" ".join(w["text"] for w in line_words))
                current_para_words.extend(line_words)
                prev_top = top

            _flush_paragraph()

    return IngestedPaper(
        title=title,
        authors=authors,
        page_count=page_count,
        paragraphs=paragraphs,
    )


def _check_quality(result: IngestedPaper) -> bool:
    """Return True if extraction quality is acceptable."""
    if result.page_count == 0:
        return False
    total_chars = sum(len(p.text) for p in result.paragraphs)
    return (total_chars / result.page_count) >= QUALITY_THRESHOLD


def ingest_pdf(pdf_bytes: bytes) -> IngestedPaper:
    """Extract structured content from a PDF. pymupdf primary, pdfplumber fallback.

    Raises IngestionError if both extractors fail.
    """
    # Try pymupdf first
    try:
        result = extract_pymupdf(pdf_bytes)
        if _check_quality(result):
            return result
        logger.info("pymupdf extraction below quality threshold, trying pdfplumber")
    except (ValueError, RuntimeError, OSError) as exc:
        logger.warning("pymupdf extraction failed: %s", exc)

    # Fallback to pdfplumber
    try:
        result = extract_pdfplumber(pdf_bytes)
        if _check_quality(result):
            return result
        logger.info("pdfplumber extraction below quality threshold")
    except (ValueError, RuntimeError, OSError) as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)

    raise IngestionError("Both pymupdf and pdfplumber failed to extract usable text from PDF")
