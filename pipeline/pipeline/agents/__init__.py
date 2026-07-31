"""Pipeline agents: protocol, real implementations, and stubs."""

from .aggregator import AggregatorAgent
from .paper_analyzer import PaperAnalyzerAgent, merge_chunk_results
from .protocol import Agent
from .stubs import (
    StubAggregator,
    StubPaperAnalyzer,
    StubThemeDedup,
    StubThemeReviewer,
)
from .theme_dedup import ThemeDedupAgent
from .theme_reviewer import ThemeReviewerAgent

__all__ = [
    "Agent",
    "AggregatorAgent",
    "PaperAnalyzerAgent",
    "StubAggregator",
    "StubPaperAnalyzer",
    "StubThemeDedup",
    "StubThemeReviewer",
    "ThemeDedupAgent",
    "ThemeReviewerAgent",
    "merge_chunk_results",
]
