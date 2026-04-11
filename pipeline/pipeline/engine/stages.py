"""Pipeline stage definitions."""

from __future__ import annotations

from enum import StrEnum


class Stage(StrEnum):
    THEME_EXTRACTION = "theme_extraction"
    CLAIM_EXTRACTION = "claim_extraction"
    THEME_DEDUP = "theme_dedup"
    THEME_REVIEW = "theme_review"
    AGGREGATION = "aggregation"


STAGES: list[Stage] = list(Stage)
TOTAL_STAGES = len(STAGES)
