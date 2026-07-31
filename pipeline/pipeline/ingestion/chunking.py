"""Two-tier chunking: heading-aware structural, embedding-similarity fallback.

Tier 1 (chunk_by_heading) groups paragraphs under each detected section
heading into a chunk. Reuses the is_heading/heading_level signal extract.py
already computes — no extra detection cost. Precise on well-structured PDFs,
free otherwise.

Tier 2 (chunk_by_similarity) splits where adjacent-paragraph embedding
similarity drops below a threshold. Fallback for PDFs where Tier 1's heading
signal is too sparse to trust (OCR'd scans, inconsistent formatting,
misfiring font-size heuristic).

chunk_paper() dispatches between them: Tier 1 first (free); if it couldn't
split at all (single chunk), that's the sparse-coverage signal, fall back to
Tier 2. Callers should use chunk_paper() — the individual tier functions are
exposed for direct testing and standalone use.
"""

from __future__ import annotations

from pipeline.config import settings
from pipeline.core.embedding import cosine_similarity, embed_batch

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


async def chunk_by_similarity(
    paragraphs: list[Paragraph], *, threshold: float | None = None
) -> list[list[Paragraph]]:
    """Tier 2: split where adjacent-paragraph embedding similarity drops below
    threshold. Fallback for PDFs where Tier 1's heading signal is too sparse
    to trust.
    """
    if len(paragraphs) <= 1:
        return [paragraphs] if paragraphs else []

    resolved_threshold = threshold if threshold is not None else settings.chunk_similarity_threshold
    vectors = await embed_batch([p.text for p in paragraphs])

    chunks: list[list[Paragraph]] = [[paragraphs[0]]]
    for i in range(1, len(paragraphs)):
        if cosine_similarity(vectors[i - 1], vectors[i]) < resolved_threshold:
            chunks.append([])
        chunks[-1].append(paragraphs[i])
    return chunks


async def chunk_paper(paragraphs: list[Paragraph]) -> list[list[Paragraph]]:
    """Dispatch: Tier 1 first (free, precise on well-structured PDFs). Tier 1's
    own output is the sparse-coverage signal — if it couldn't split at all
    (single chunk), heading coverage was too sparse to trust; fall back to
    Tier 2 embedding-similarity chunking.
    """
    structural_chunks = chunk_by_heading(paragraphs)
    if len(structural_chunks) > 1:
        return structural_chunks
    return await chunk_by_similarity(paragraphs)
