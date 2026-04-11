"""Theme dedup agent: groups semantically equivalent themes across papers."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.parsing import run_agent_with_retry
from pipeline.agents.prompts.theme_dedup import THEME_DEDUP_PROMPT

# --- Pydantic output models ---


class ThemeGroup(BaseModel):
    """A group of semantically equivalent themes."""

    canonical_name: str
    description: str
    member_indices: list[int] = Field(min_length=1)


class ThemeDedupResult(BaseModel):
    """Structured output from the theme dedup LLM."""

    groups: list[ThemeGroup] = Field(min_length=1)


# --- Agent ---


class ThemeDedupAgent:
    """Groups semantically equivalent themes across all papers.

    Runs as a sync barrier — receives all themes from all papers,
    returns canonical theme map with aliases. Wraps an Agno agent
    internally but satisfies the pipeline Agent protocol.
    """

    def __init__(self) -> None:
        self._agent = AgnoAgent(
            name="ThemeDedup",
            model=create_model(),
            instructions=THEME_DEDUP_PROMPT,
            structured_outputs=True,
        )

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        all_themes: list[dict[str, Any]] = input["themes"]

        # Build numbered list for LLM
        lines = []
        for i, theme in enumerate(all_themes):
            name = theme.get("name", theme.get("label", "Unknown"))
            desc = theme.get("description", "")
            paper_id = theme.get("paper_id", "unknown")
            lines.append(f"[{i}] {name} — {desc} (paper: {paper_id})")

        message = "\n".join(lines)

        dedup = await run_agent_with_retry(
            self._agent, message, ThemeDedupResult,
        )

        # Map LLM groups back to concrete theme data
        theme_map: dict[str, list[str]] = {}
        canonical_themes: list[dict[str, Any]] = []

        for group in dedup.groups:
            canonical_id = str(uuid4())
            source_ids: list[str] = []
            paper_ids: list[str] = []
            aliases: list[str] = []

            for idx in group.member_indices:
                if 0 <= idx < len(all_themes):
                    source = all_themes[idx]
                    source_ids.append(source["id"])
                    pid = source.get("paper_id", "")
                    if pid and pid not in paper_ids:
                        paper_ids.append(pid)
                    name = source.get("name", source.get("label", ""))
                    if name and name not in aliases:
                        aliases.append(name)

            theme_map[canonical_id] = source_ids
            canonical_themes.append({
                "id": canonical_id,
                "name": group.canonical_name,
                "label": group.canonical_name,
                "description": group.description,
                "paper_ids": paper_ids,
                "aliases": aliases,
                "source_theme_ids": source_ids,
            })

        return {
            "theme_map": theme_map,
            "themes": canonical_themes,
        }
