"""Theme dedup agent: groups semantically equivalent themes across papers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from itertools import combinations
from typing import Any
from uuid import uuid4

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.nli import GROUP_CONTRADICTION_THRESHOLD, GroupEquivalenceVerifier
from pipeline.agents.parsing import reask, run_agent_with_retry
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
        from pipeline.config import settings

        self._agent = AgnoAgent(
            name="ThemeDedup",
            model=create_model(),
            instructions=THEME_DEDUP_PROMPT,
            output_schema=ThemeDedupResult,
            structured_outputs=True,
            debug_mode=settings.llm_debug_mode,
        )
        # Own DeBERTa instance, independent of theme_reviewer.py's (d-019).
        self._verifier = GroupEquivalenceVerifier()

    async def run(
        self,
        data: dict[str, Any],
        *,
        on_event: Callable[[Any], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        all_themes: list[dict[str, Any]] = data["themes"]

        # Build numbered list for LLM
        lines = []
        for i, theme in enumerate(all_themes):
            name = theme.get("name", theme.get("label", "Unknown"))
            desc = theme.get("description", "")
            paper_id = theme.get("paper_id", "unknown")
            lines.append(f"[{i}] {name} — {desc} (paper: {paper_id})")

        message = "\n".join(lines)

        dedup = await run_agent_with_retry(
            self._agent,
            message,
            ThemeDedupResult,
            context={
                "stage": "theme_dedup",
                "theme_count": len(all_themes),
                "raw_theme_count": len(all_themes),
            },
            on_event=on_event,
        )

        out_of_range = [
            (group.canonical_name, idx)
            for group in dedup.groups
            for idx in group.member_indices
            if not (0 <= idx < len(all_themes))
        ]
        if out_of_range:
            offenders = "; ".join(
                f"group '{name}' references index {idx}" for name, idx in out_of_range
            )
            original_dedup = dedup
            dedup = await reask(
                self._agent,
                message,
                f"{offenders}. Valid indices are 0..{len(all_themes) - 1}.",
                ThemeDedupResult,
                fallback=lambda: original_dedup,
                context={
                    "stage": "theme_dedup",
                    "theme_count": len(all_themes),
                    "raw_theme_count": len(all_themes),
                },
                on_event=on_event,
            )

        # DeBERTa cross-encoder verification (§6.1): for each multi-member
        # group, check every member-pair both directions. A group is flagged
        # only when BOTH directions predict contradiction above threshold —
        # see agents/nli.py's GROUP_CONTRADICTION_THRESHOLD comment for why
        # this replaces the design doc's literal argmax rule.
        pairs: list[tuple[str, str]] = []
        pair_owners: list[tuple[ThemeGroup, int, int]] = []
        for group in dedup.groups:
            valid_indices = [i for i in group.member_indices if 0 <= i < len(all_themes)]
            for a, b in combinations(valid_indices, 2):
                text_a = f"{all_themes[a].get('name', '')}: {all_themes[a].get('description', '')}"
                text_b = f"{all_themes[b].get('name', '')}: {all_themes[b].get('description', '')}"
                pairs.append((text_a, text_b))
                pairs.append((text_b, text_a))
                pair_owners.append((group, a, b))

        if pairs:
            contradiction_probs = await asyncio.to_thread(self._verifier.contradiction_probs, pairs)
            contradicted = [
                (group, a, b)
                for i, (group, a, b) in enumerate(pair_owners)
                if contradiction_probs[2 * i] >= GROUP_CONTRADICTION_THRESHOLD
                and contradiction_probs[2 * i + 1] >= GROUP_CONTRADICTION_THRESHOLD
            ]
            if contradicted:
                offenders = "; ".join(
                    f"themes at indices {a} and {b} were grouped as '{group.canonical_name}' "
                    "but do not appear semantically equivalent"
                    for group, a, b in contradicted
                )
                pre_verification_dedup = dedup
                dedup = await reask(
                    self._agent,
                    message,
                    f"{offenders}. Reconsider these groupings.",
                    ThemeDedupResult,
                    fallback=lambda: pre_verification_dedup,
                    context={
                        "stage": "theme_dedup",
                        "theme_count": len(all_themes),
                        "raw_theme_count": len(all_themes),
                    },
                    on_event=on_event,
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
            canonical_themes.append(
                {
                    "id": canonical_id,
                    "name": group.canonical_name,
                    "label": group.canonical_name,
                    "description": group.description,
                    "paper_ids": paper_ids,
                    "aliases": aliases,
                    "source_theme_ids": source_ids,
                }
            )

        return {
            "theme_map": theme_map,
            "themes": canonical_themes,
        }
