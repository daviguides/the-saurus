"""Custom Colang actions backing the topic gate flow (flow.co)."""

from __future__ import annotations

from pipeline.ingestion.extract import QUALITY_THRESHOLD


async def check_quality_action(
    content: str = "", page_count: int = 0, **kwargs,
) -> bool:
    # content is annotated markdown (IngestedPaper.to_annotated_markdown()),
    # not the raw paragraph text QUALITY_THRESHOLD was calibrated against —
    # position tags inflate the char count slightly, biasing toward accept.
    if page_count <= 0:
        return False
    return (len(content) / page_count) >= QUALITY_THRESHOLD


async def check_metadata_action(
    title: str = "", authors: list[str] | None = None, **kwargs,
) -> bool:
    return bool(title) and bool(authors)
