"""Pipeline agents: protocol, real implementations, and stubs."""

from .protocol import Agent
from .stubs import (
    StubAggregator,
    StubClaimExtractor,
    StubThemeDedup,
    StubThemeExtractor,
    StubThemeReviewer,
)
from .claim_extractor import ClaimExtractorAgent
from .theme_dedup import ThemeDedupAgent
from .theme_extractor import ThemeExtractorAgent
from .theme_reviewer import ThemeReviewerAgent

__all__ = [
    "Agent",
    "ClaimExtractorAgent",
    "StubAggregator",
    "StubClaimExtractor",
    "StubThemeDedup",
    "StubThemeExtractor",
    "StubThemeReviewer",
    "ThemeDedupAgent",
    "ThemeExtractorAgent",
    "ThemeReviewerAgent",
]
