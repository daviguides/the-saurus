"""Pydantic models for PDF ingestion output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Paragraph(BaseModel):
    """A single paragraph extracted from a PDF, tagged with positional metadata."""

    page: int
    index: int
    text: str
    is_heading: bool = False
    heading_level: int = 0  # 1 = title, 2 = section heading, 0 = body


class IngestedPaper(BaseModel):
    """Structured output of PDF ingestion with paragraph-level metadata."""

    title: str = ""
    authors: list[str] = Field(default_factory=list)
    page_count: int = 0
    paragraphs: list[Paragraph] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Render paragraphs as Markdown with heading formatting."""
        lines: list[str] = []
        for p in self.paragraphs:
            if p.is_heading:
                prefix = "#" * max(p.heading_level, 1)
                lines.append(f"{prefix} {p.text}")
            else:
                lines.append(p.text)
            lines.append("")  # blank line between paragraphs
        return "\n".join(lines).rstrip("\n") + "\n"

    def to_annotated_markdown(self) -> str:
        """Render paragraphs as Markdown with [p.X,§Y] position annotations."""
        lines: list[str] = []
        for p in self.paragraphs:
            tag = f"[p.{p.page},§{p.index}]"
            if p.is_heading:
                prefix = "#" * max(p.heading_level, 1)
                lines.append(f"{prefix} {tag} {p.text}")
            else:
                lines.append(f"{tag} {p.text}")
            lines.append("")  # blank line between paragraphs
        return "\n".join(lines).rstrip("\n") + "\n"
