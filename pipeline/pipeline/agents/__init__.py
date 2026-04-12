"""Pipeline agents: protocol, real implementations, and stubs."""

from .protocol import Agent
from .stubs import (
    StubAggregator,
    StubPaperAnalyzer,
    StubThemeDedup,
    StubThemeReviewer,
)
from .aggregator import AggregatorAgent
from .paper_analyzer import PaperAnalyzerAgent
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
]
