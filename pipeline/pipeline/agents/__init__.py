"""Pipeline agents: protocol and stub implementations."""

from .protocol import Agent
from .stubs import (
    StubAggregator,
    StubClaimExtractor,
    StubThemeDedup,
    StubThemeExtractor,
    StubThemeReviewer,
)

__all__ = [
    "Agent",
    "StubAggregator",
    "StubClaimExtractor",
    "StubThemeDedup",
    "StubThemeExtractor",
    "StubThemeReviewer",
]
