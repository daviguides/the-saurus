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
    before the first section heading — stays in chunk 0 rather than becoming
    its own theme-less chunk.
    """
    if not paragraphs:
        return []

    chunks: list[list[Paragraph]] = [[]]
    for p in paragraphs:
        if p.heading_level == 2 and chunks[-1]:
            chunks.append([])
        chunks[-1].append(p)

    return chunks
