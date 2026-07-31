"""PDF ingestion: convert PDFs to structured paragraphs with metadata."""

from .chunking import chunk_by_heading
from .extract import IngestionError, ingest_pdf
from .models import IngestedPaper, Paragraph, render_annotated_markdown

__all__ = [
    "IngestedPaper",
    "IngestionError",
    "Paragraph",
    "chunk_by_heading",
    "ingest_pdf",
    "render_annotated_markdown",
]
