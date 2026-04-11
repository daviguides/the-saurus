"""PDF ingestion: convert PDFs to structured paragraphs with metadata."""

from .extract import IngestionError, ingest_pdf
from .models import IngestedPaper, Paragraph

__all__ = ["IngestedPaper", "IngestionError", "Paragraph", "ingest_pdf"]
