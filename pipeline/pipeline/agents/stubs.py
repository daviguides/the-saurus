"""Pass-through stub agents for pipeline engine validation."""

from __future__ import annotations

from typing import Any
from uuid import uuid4


class StubThemeExtractor:
    """Returns placeholder themes for a single paper."""

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        paper_id = input["paper_id"]
        title = input.get("title", "Untitled")
        theme_id = str(uuid4())
        return {
            "themes": [
                {
                    "id": theme_id,
                    "label": f"Theme from {title}",
                    "description": f"Stub theme extracted from paper {paper_id}",
                    "paper_id": paper_id,
                }
            ]
        }


class StubClaimExtractor:
    """Returns placeholder claims for a single paper."""

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        paper_id = input["paper_id"]
        title = input.get("title", "Untitled")
        claim_id = str(uuid4())
        return {
            "claims": [
                {
                    "id": claim_id,
                    "text": f"Stub claim from {title}",
                    "source": {
                        "paper_id": paper_id,
                        "page": 1,
                        "paragraph": 1,
                    },
                }
            ]
        }


class StubThemeDedup:
    """Passes all themes through as canonical (no actual dedup)."""

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        all_themes = input["themes"]
        theme_map = {t["id"]: [t["id"]] for t in all_themes}
        return {
            "theme_map": theme_map,
            "themes": all_themes,
        }


class StubThemeReviewer:
    """Returns a placeholder review for a single theme."""

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        theme = input["theme"]
        claims = input.get("claims", [])
        return {
            "theme_id": theme["id"],
            "label": theme["label"],
            "review": f"Stub review of theme: {theme['label']}",
            "claim_ids": [c["id"] for c in claims],
        }


class StubAggregator:
    """Returns a placeholder literature review from theme reviews."""

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        theme_reviews = input["theme_reviews"]
        sections = [
            {
                "theme_id": tr["theme_id"],
                "label": tr["label"],
                "content": tr["review"],
                "claim_ids": tr["claim_ids"],
            }
            for tr in theme_reviews
        ]
        return {
            "title": "Literature Review",
            "sections": sections,
            "references": [],
        }
