"""Pass-through stub agents for pipeline engine validation."""

from __future__ import annotations

from typing import Any
from uuid import uuid4


class StubPaperAnalyzer:
    """Returns placeholder themes and claims for a single paper."""

    async def run(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        paper_id = data["paper_id"]
        title = data.get("title", "Untitled")
        theme_id = str(uuid4())
        claim_id = str(uuid4())
        return {
            "themes": [
                {
                    "id": theme_id,
                    "name": f"Theme from {title}",
                    "description": f"Stub theme extracted from paper {paper_id}",
                    "paper_id": paper_id,
                    "positions": [{"page": 1, "paragraph": 1}],
                }
            ],
            "claims": [
                {
                    "id": claim_id,
                    "theme_id": theme_id,
                    "theme_name": f"Theme from {title}",
                    "text": f"Stub claim from {title}",
                    "page": 1,
                    "paragraph": 1,
                    "deep": "Stub deep analysis",
                    "summary": f"Stub claim from {title}",
                    "paper_id": paper_id,
                }
            ],
        }


class StubThemeDedup:
    """Passes all themes through as canonical (no actual dedup)."""

    async def run(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        all_themes = data["themes"]
        theme_map = {t["id"]: [t["id"]] for t in all_themes}
        return {
            "theme_map": theme_map,
            "themes": all_themes,
        }


class StubThemeReviewer:
    """Returns a placeholder review for a single theme."""

    async def run(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        theme = data["theme"]
        claims = data.get("claims", [])
        return {
            "theme_id": theme["id"],
            "label": theme.get("label", theme.get("name", "")),
            "review": f"Stub review of theme: {theme.get('label', theme.get('name', ''))}",
            "claim_ids": [c["id"] for c in claims],
        }

    async def run_batch(
        self,
        themes: list[dict[str, Any]],
        all_claims: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        results = []
        for theme in themes:
            result = await self.run({"theme": theme, "claims": all_claims})
            results.append(result)
        return results


class StubAggregator:
    """Returns a placeholder literature review from theme reviews."""

    async def run(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        theme_reviews = data["theme_reviews"]
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
