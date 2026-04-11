"""Pipeline agents: protocol, real implementations, and stubs."""

from .protocol import Agent
from .stubs import (
    StubAggregator,
    StubClaimExtractor,
    StubThemeDedup,
    StubThemeExtractor,
    StubThemeReviewer,
)
from .aggregator import AggregatorAgent
from .paper_analyzer import PaperAnalyzerAgent
from .theme_dedup import ThemeDedupAgent
from .theme_reviewer import ThemeReviewerAgent

# Legacy — kept for backward compatibility but PaperAnalyzerAgent replaces both
from .claim_extractor import ClaimExtractorAgent
from .theme_extractor import ThemeExtractorAgent

__all__ = [
    "Agent",
    "AggregatorAgent",
    "ClaimExtractorAgent",
    "PaperAnalyzerAgent",
    "StubAggregator",
    "StubClaimExtractor",
    "StubThemeDedup",
    "StubThemeExtractor",
    "StubThemeReviewer",
    "ThemeDedupAgent",
    "ThemeExtractorAgent",
    "ThemeReviewerAgent",
]
