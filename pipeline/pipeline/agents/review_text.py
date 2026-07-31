"""Shared review-text assembly, used by both the judge gate and the toxic gate.

Extracted so both gate clients score the exact same title+abstract+sections
text instead of each maintaining their own concatenation logic.
"""

from __future__ import annotations

from typing import Any


def build_review_text(review: dict[str, Any]) -> str:
    """Flatten title/abstract/sections into the text a gate scores."""
    sections_text = "\n\n".join(
        f"## {s.get('label', '')}\n{s.get('content', '')}"
        for s in review.get("sections", [])
    )
    return f"# {review.get('title', '')}\n\n{review.get('abstract', '')}\n\n{sections_text}"
