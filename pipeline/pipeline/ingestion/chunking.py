"""Tier 1 chunking: heading-aware structural splitting.

Groups paragraphs under each detected section heading into a chunk. Reuses
the is_heading/heading_level signal extract.py already computes — no extra
detection cost. A paper with no detected section headings degrades to a
single chunk (the sparse-heading-coverage case Tier 2, embedding-based
chunking, exists to address — out of scope here).
"""

from __future__ import annotations

from .models import Paragraph


def chunk_by_heading(paragraphs: list[Paragraph]) -> list[list[Paragraph]]:
    """Split paragraphs into chunks at each section heading (heading_level == 2).

    Front matter — title, authors, abstract-without-heading, i.e. everything
    before the first section heading — merges into that first section's
    chunk rather than becoming its own front-matter-only chunk, which would
    almost always yield zero extractable themes (min_length=1 failure).
    """
    if not paragraphs:
        return []

    chunks: list[list[Paragraph]] = [[]]
    seen_section_heading = False
    for p in paragraphs:
        if p.heading_level == 2:
            if seen_section_heading:
                chunks.append([])
            seen_section_heading = True
        chunks[-1].append(p)

    return chunks
