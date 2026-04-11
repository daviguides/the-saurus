"""Tests for theme dedup agent: Pydantic models, agent protocol, agent run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.agents.protocol import Agent
from pipeline.agents.theme_dedup import (
    ThemeDedupAgent,
    ThemeDedupResult,
    ThemeGroup,
)

# --- Pydantic model tests ---


class TestPydanticModels:
    def test_theme_group_valid(self) -> None:
        group = ThemeGroup(
            canonical_name="Chronobiology",
            description="Study of biological rhythms.",
            member_indices=[0, 2, 5],
        )
        assert group.canonical_name == "Chronobiology"
        assert len(group.member_indices) == 3

    def test_theme_group_requires_members(self) -> None:
        with pytest.raises(Exception):
            ThemeGroup(
                canonical_name="Test",
                description="Desc",
                member_indices=[],
            )

    def test_dedup_result_valid(self) -> None:
        result = ThemeDedupResult(
            groups=[
                ThemeGroup(
                    canonical_name="Gene Therapy",
                    description="Genetic interventions.",
                    member_indices=[0, 1],
                ),
            ]
        )
        assert len(result.groups) == 1

    def test_dedup_result_requires_groups(self) -> None:
        with pytest.raises(Exception):
            ThemeDedupResult(groups=[])


# --- Agent protocol tests ---


class TestAgentProtocol:
    def test_satisfies_protocol(self) -> None:
        with patch("pipeline.agents.theme_dedup.AgnoAgent"):
            agent = ThemeDedupAgent()
        assert isinstance(agent, Agent)


# --- Agent run tests ---


@dataclass
class FakeRunOutput:
    content: Any


def _make_input_themes() -> list[dict[str, Any]]:
    """Build a realistic set of themes from 3 papers with some semantic overlap."""
    return [
        {
            "id": "t1",
            "name": "Chronobiology",
            "description": "Study of biological rhythms and circadian cycles.",
            "paper_id": "p1",
            "positions": [{"page": 1, "paragraph": 2}],
        },
        {
            "id": "t2",
            "name": "Gene Therapy",
            "description": "Therapeutic delivery of genetic material.",
            "paper_id": "p1",
            "positions": [{"page": 3, "paragraph": 1}],
        },
        {
            "id": "t3",
            "name": "Circadian Biology",
            "description": "Mechanisms of the circadian clock.",
            "paper_id": "p2",
            "positions": [{"page": 2, "paragraph": 3}],
        },
        {
            "id": "t4",
            "name": "Immunogenicity",
            "description": "Immune response to therapeutic agents.",
            "paper_id": "p2",
            "positions": [{"page": 5, "paragraph": 1}],
        },
        {
            "id": "t5",
            "name": "Biological Rhythms",
            "description": "Cyclical patterns in living organisms.",
            "paper_id": "p3",
            "positions": [{"page": 1, "paragraph": 1}],
        },
    ]


def _make_dedup_result() -> ThemeDedupResult:
    """LLM groups chronobiology variants together, keeps others as singletons."""
    return ThemeDedupResult(
        groups=[
            ThemeGroup(
                canonical_name="Chronobiology",
                description="Study of biological rhythms, circadian cycles, and cyclical patterns in organisms.",
                member_indices=[0, 2, 4],
            ),
            ThemeGroup(
                canonical_name="Gene Therapy",
                description="Therapeutic delivery of genetic material.",
                member_indices=[1],
            ),
            ThemeGroup(
                canonical_name="Immunogenicity",
                description="Immune response to therapeutic agents.",
                member_indices=[3],
            ),
        ]
    )


class TestThemeDedupAgentRun:
    @pytest.fixture
    def input_themes(self) -> list[dict[str, Any]]:
        return _make_input_themes()

    @pytest.fixture
    def mock_dedup(self) -> ThemeDedupResult:
        return _make_dedup_result()

    async def test_run_merges_duplicate_themes(
        self, input_themes: list[dict[str, Any]], mock_dedup: ThemeDedupResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_dedup)

        with patch("pipeline.agents.theme_dedup.AgnoAgent"):
            agent = ThemeDedupAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"themes": input_themes})

        canonical = result["themes"]
        assert len(canonical) == 3

        # Chronobiology group merged 3 themes from 3 papers
        chrono = next(t for t in canonical if t["name"] == "Chronobiology")
        assert set(chrono["paper_ids"]) == {"p1", "p2", "p3"}
        assert set(chrono["aliases"]) == {"Chronobiology", "Circadian Biology", "Biological Rhythms"}
        assert set(chrono["source_theme_ids"]) == {"t1", "t3", "t5"}

    async def test_run_singleton_themes_preserved(
        self, input_themes: list[dict[str, Any]], mock_dedup: ThemeDedupResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_dedup)

        with patch("pipeline.agents.theme_dedup.AgnoAgent"):
            agent = ThemeDedupAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"themes": input_themes})

        canonical = result["themes"]
        immuno = next(t for t in canonical if t["name"] == "Immunogenicity")
        assert immuno["paper_ids"] == ["p2"]
        assert immuno["aliases"] == ["Immunogenicity"]
        assert immuno["source_theme_ids"] == ["t4"]

    async def test_run_theme_map_correct(
        self, input_themes: list[dict[str, Any]], mock_dedup: ThemeDedupResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_dedup)

        with patch("pipeline.agents.theme_dedup.AgnoAgent"):
            agent = ThemeDedupAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"themes": input_themes})

        theme_map = result["theme_map"]
        assert len(theme_map) == 3

        # Each canonical ID maps to source IDs
        for canonical_theme in result["themes"]:
            cid = canonical_theme["id"]
            assert cid in theme_map
            assert theme_map[cid] == canonical_theme["source_theme_ids"]

    async def test_run_generates_unique_ids(
        self, input_themes: list[dict[str, Any]], mock_dedup: ThemeDedupResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_dedup)

        with patch("pipeline.agents.theme_dedup.AgnoAgent"):
            agent = ThemeDedupAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"themes": input_themes})

        ids = [t["id"] for t in result["themes"]]
        assert len(set(ids)) == len(ids)

    async def test_run_all_source_themes_covered(
        self, input_themes: list[dict[str, Any]], mock_dedup: ThemeDedupResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_dedup)

        with patch("pipeline.agents.theme_dedup.AgnoAgent"):
            agent = ThemeDedupAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"themes": input_themes})

        # Every input theme ID must appear in exactly one group
        all_source_ids: list[str] = []
        for t in result["themes"]:
            all_source_ids.extend(t["source_theme_ids"])

        input_ids = {t["id"] for t in input_themes}
        assert set(all_source_ids) == input_ids
        assert len(all_source_ids) == len(input_ids)  # no duplicates

    async def test_run_passes_numbered_list_to_agno(
        self, input_themes: list[dict[str, Any]], mock_dedup: ThemeDedupResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_dedup)

        with patch("pipeline.agents.theme_dedup.AgnoAgent"):
            agent = ThemeDedupAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        await agent.run({"themes": input_themes})

        call_args = agent._agent.arun.call_args
        message = call_args[0][0]

        # Verify numbered format
        assert "[0] Chronobiology" in message
        assert "[1] Gene Therapy" in message
        assert "[2] Circadian Biology" in message
        assert "(paper: p1)" in message
        assert "(paper: p2)" in message

    async def test_run_canonical_has_label_field(
        self, input_themes: list[dict[str, Any]], mock_dedup: ThemeDedupResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_dedup)

        with patch("pipeline.agents.theme_dedup.AgnoAgent"):
            agent = ThemeDedupAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"themes": input_themes})

        for t in result["themes"]:
            assert t["label"] == t["name"]
