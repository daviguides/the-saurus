"""Tests for the Colang topic gate (pipeline.agents.gate)."""

from __future__ import annotations

import pytest

from pipeline.agents.gate import evaluate_topic_gate
from pipeline.ingestion.extract import QUALITY_THRESHOLD

GOOD_TITLE = "A Real Paper Title"
GOOD_AUTHORS = ["A. Author"]


def _good_content(page_count: int) -> str:
    """Content comfortably above QUALITY_THRESHOLD chars-per-page."""
    return "x" * (QUALITY_THRESHOLD * page_count * 2)


@pytest.mark.asyncio
async def test_gate_accepts_good_paper() -> None:
    """A paper with sufficient quality and both title/authors is accepted."""
    result = await evaluate_topic_gate(
        content=_good_content(page_count=2),
        page_count=2,
        title=GOOD_TITLE,
        authors=GOOD_AUTHORS,
    )
    assert result.verdict == "accept"
    assert result.reason is None


@pytest.mark.asyncio
async def test_gate_rejects_low_quality() -> None:
    """A paper below the chars-per-page threshold is rejected."""
    result = await evaluate_topic_gate(
        content="short",
        page_count=1,
        title=GOOD_TITLE,
        authors=GOOD_AUTHORS,
    )
    assert result.verdict == "reject"
    assert result.reason is not None


@pytest.mark.asyncio
async def test_gate_rejects_missing_title() -> None:
    """A paper with no detected title is rejected even with good quality/authors."""
    result = await evaluate_topic_gate(
        content=_good_content(page_count=2),
        page_count=2,
        title="",
        authors=GOOD_AUTHORS,
    )
    assert result.verdict == "reject"
    assert result.reason is not None


@pytest.mark.asyncio
async def test_gate_rejects_missing_authors() -> None:
    """A paper with no detected authors is rejected even with good quality/title."""
    result = await evaluate_topic_gate(
        content=_good_content(page_count=2),
        page_count=2,
        title=GOOD_TITLE,
        authors=[],
    )
    assert result.verdict == "reject"
    assert result.reason is not None
