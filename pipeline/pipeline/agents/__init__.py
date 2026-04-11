"""Pipeline agents: protocol, real implementations, and stubs."""

from .protocol import Agent
from .stubs import (
    StubAggregator,
    StubClaimExtractor,
    StubThemeDedup,
    StubThemeExtractor,
    StubThemeReviewer,
)
from .theme_extractor import ThemeExtractorAgent

__all__ = [
    "Agent",
    "StubAggregator",
    "StubClaimExtractor",
    "StubThemeDedup",
    "StubThemeExtractor",
    "StubThemeReviewer",
    "ThemeExtractorAgent",
]
