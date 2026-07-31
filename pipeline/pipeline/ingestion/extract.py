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

        # Single pass: collect raw block data AND body font sizes together
        body_sizes: list[float] = []
        raw_blocks: list[tuple[int, int, str, float, bool]] = []
        # Each raw_block: (page_idx, block_idx, block_text, block_max_size, has_bold)

        for page_idx, page in enumerate(doc):
            d = page.get_text("dict")

            for block_idx, block in enumerate(d["blocks"]):
                if block["type"] != 0:
                    continue

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
                        elif span["text"].strip():
                            body_sizes.append(span["size"])
                    block_text_parts.append(line_text)

                block_text = "\n".join(block_text_parts).strip()
                if not block_text:
                    continue

                raw_blocks.append((page_idx, block_idx, block_text, block_max_size, has_bold))

        # Compute median body font size from collected data
        median_body_size = median(body_sizes) if body_sizes else 10.0
        heading_threshold = median_body_size + 1.0

        # Classify headings using the median (iterates in-memory list, not PDF)
        paragraphs: list[Paragraph] = []
        title = ""
        authors: list[str] = []
        max_font_size_page1 = 0.0
        title_block_idx: int | None = None
        prev_page_idx = -1
        para_idx = 0

        for page_idx, block_idx, block_text, block_max_size, has_bold in raw_blocks:
            if page_idx != prev_page_idx:
                para_idx = 0
                prev_page_idx = page_idx

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

        # Single pass: extract words once per page, store for reuse
        body_sizes: list[float] = []
        pages_words: list[list[dict]] = []
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["fontname", "size"])
            pages_words.append(words)
            for w in words:
                if "Bold" not in w.get("fontname", ""):
                    body_sizes.append(w.get("size", 10.0))

        median_body_size = median(body_sizes) if body_sizes else 10.0
        heading_threshold = median_body_size + 1.0
        line_height = median_body_size * 1.4  # approximate leading

        paragraphs: list[Paragraph] = []
        title = ""
        authors: list[str] = []
        max_font_size_page1 = 0.0
        title_found = False

        for page_idx, words in enumerate(pages_words):
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


# PII entity scope: emails/phones/addresses only, deliberately excludes PERSON
# so author names survive for citations (§3.2's output-side pass handles PERSON).
_PII_ENTITIES = ["EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION"]

_analyzer = None
_anonymizer = None


def _get_engines():
    """Lazily build and cache the Presidio engines (loads the spaCy model)."""
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_anonymizer import AnonymizerEngine

        nlp_engine = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
        ).create_engine()
        _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


def _scrub_pii(paragraphs: list[Paragraph]) -> list[Paragraph]:
    """Redact emails/phones/addresses from paragraph text. Redact + log, never block."""
    from presidio_anonymizer.entities import OperatorConfig

    analyzer, anonymizer = _get_engines()
    operators = {
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
        "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
    }
    scrubbed: list[Paragraph] = []
    for p in paragraphs:
        results = analyzer.analyze(text=p.text, language="en", entities=_PII_ENTITIES)
        if not results:
            scrubbed.append(p)
            continue
        anonymized = anonymizer.anonymize(
            text=p.text, analyzer_results=results, operators=operators
        )
        for item in anonymized.items:
            logger.info(
                "PII redacted: type=%s page=%d paragraph=%d", item.entity_type, p.page, p.index
            )
        scrubbed.append(p.model_copy(update={"text": anonymized.text}))
    return scrubbed


def ingest_pdf(pdf_bytes: bytes) -> IngestedPaper:
    """Extract structured content from a PDF. pymupdf primary, pdfplumber fallback.

    Raises IngestionError if both extractors fail.
    """
    # Try pymupdf first
    try:
        result = extract_pymupdf(pdf_bytes)
        if _check_quality(result):
            result.paragraphs = _scrub_pii(result.paragraphs)
            return result
        logger.info("pymupdf extraction below quality threshold, trying pdfplumber")
    except (ValueError, RuntimeError, OSError) as exc:
        logger.warning("pymupdf extraction failed: %s", exc)

    # Fallback to pdfplumber
    try:
        result = extract_pdfplumber(pdf_bytes)
        if _check_quality(result):
            result.paragraphs = _scrub_pii(result.paragraphs)
            return result
        logger.info("pdfplumber extraction below quality threshold")
    except (ValueError, RuntimeError, OSError) as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)

    raise IngestionError("Both pymupdf and pdfplumber failed to extract usable text from PDF")
