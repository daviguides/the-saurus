"""Tests for aggregator agent: helpers, citation resolution, and agent run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.agents.aggregator import (
    AggregatorAgent,
    AggregatorResult,
    ReviewCitation,
    ReviewSection,
    _build_claim_lookup,
    _build_message,
    _build_references,
    _collect_claim_ids,
    _resolve_citations,
)
from pipeline.agents.protocol import Agent


# --- Fixtures ---


def _make_claims() -> list[dict[str, Any]]:
    return [
        {
            "id": "c1",
            "theme_id": "st1",
            "theme_name": "Chronobiology",
            "text": "Circadian clock regulates metabolism.",
            "page": 2,
            "paragraph": 3,
            "deep": "Full context about circadian regulation.",
            "summary": "Clock regulates metabolism.",
            "source": {"paper_id": "p1", "page": 2, "paragraph": 3},
        },
        {
            "id": "c2",
            "theme_id": "st2",
            "theme_name": "Circadian Biology",
            "text": "Light exposure resets the SCN.",
            "page": 4,
            "paragraph": 1,
            "deep": "Full context about light and SCN.",
            "summary": "Light resets SCN.",
            "source": {"paper_id": "p2", "page": 4, "paragraph": 1},
        },
        {
            "id": "c3",
            "theme_id": "st3",
            "theme_name": "Gene Therapy",
            "text": "AAV vectors deliver cargo.",
            "page": 5,
            "paragraph": 2,
            "deep": "Full context about AAV.",
            "summary": "AAV delivers cargo.",
            "source": {"paper_id": "p1", "page": 5, "paragraph": 2},
        },
    ]


def _make_theme_reviews() -> list[dict[str, Any]]:
    return [
        {
            "theme_id": "t1",
            "label": "Chronobiology",
            "review": "Two papers demonstrate circadian regulation.",
            "consensus": ["Both confirm circadian rhythms influence physiology."],
            "disagreements": ["Paper 1 emphasizes metabolism, paper 2 neural mechanisms."],
            "gaps": ["No study examines immune function."],
            "claim_ids": ["c1", "c2"],
            "key_claims": [
                {"claim_id": "c1", "paper_id": "p1", "summary": "Clock regulates metabolism."},
                {"claim_id": "c2", "paper_id": "p2", "summary": "Light resets SCN."},
            ],
        },
        {
            "theme_id": "t2",
            "label": "Gene Therapy",
            "review": "AAV vectors show promise for delivery.",
            "consensus": ["AAV9 is effective for CNS targeting."],
            "disagreements": [],
            "gaps": ["Long-term safety data missing."],
            "claim_ids": ["c3"],
            "key_claims": [
                {"claim_id": "c3", "paper_id": "p1", "summary": "AAV delivers cargo."},
            ],
        },
    ]


def _make_papers() -> list[dict[str, Any]]:
    return [
        {"paper_id": "p1", "title": "Circadian Metabolism Study", "authors": ["Smith J", "Doe A"]},
        {"paper_id": "p2", "title": "Light and the SCN", "authors": ["Lee K"]},
    ]


# --- Pydantic model tests ---


class TestPydanticModels:
    def test_review_citation_valid(self) -> None:
        cit = ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1")
        assert cit.ref_number == 1

    def test_review_section_valid(self) -> None:
        section = ReviewSection(
            theme_id="t1",
            label="Chrono",
            content="Some text [1] and [2].",
            citation_refs=[1, 2],
        )
        assert section.theme_id == "t1"

    def test_review_section_requires_content(self) -> None:
        with pytest.raises(Exception):
            ReviewSection(theme_id="t1", label="X", content="", citation_refs=[])

    def test_aggregator_result_valid(self) -> None:
        result = AggregatorResult(
            title="Literature Review",
            abstract="A review.",
            sections=[
                ReviewSection(theme_id="t1", label="X", content="Text.", citation_refs=[]),
            ],
            citations=[],
        )
        assert result.title == "Literature Review"

    def test_aggregator_result_requires_title(self) -> None:
        with pytest.raises(Exception):
            AggregatorResult(
                title="",
                abstract="A review.",
                sections=[
                    ReviewSection(theme_id="t1", label="X", content="Text.", citation_refs=[]),
                ],
            )

    def test_aggregator_result_requires_sections(self) -> None:
        with pytest.raises(Exception):
            AggregatorResult(
                title="Title",
                abstract="A review.",
                sections=[],
            )


# --- Agent protocol tests ---


class TestAgentProtocol:
    def test_satisfies_protocol(self) -> None:
        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()
        assert isinstance(agent, Agent)


# --- Helper function tests ---


class TestBuildClaimLookup:
    def test_builds_lookup_by_id(self) -> None:
        claims = _make_claims()
        lookup = _build_claim_lookup(claims)
        assert "c1" in lookup
        assert "c2" in lookup
        assert "c3" in lookup
        assert lookup["c1"]["source"]["page"] == 2

    def test_skips_claims_without_id(self) -> None:
        claims = [{"text": "no id"}]
        lookup = _build_claim_lookup(claims)
        assert len(lookup) == 0


class TestBuildMessage:
    def test_includes_all_theme_labels(self) -> None:
        reviews = _make_theme_reviews()
        claim_lookup = _build_claim_lookup(_make_claims())
        _registry, msg = _build_message(reviews, claim_lookup)
        assert "Chronobiology" in msg
        assert "Gene Therapy" in msg

    def test_includes_claim_registry(self) -> None:
        reviews = _make_theme_reviews()
        claim_lookup = _build_claim_lookup(_make_claims())
        registry, msg = _build_message(reviews, claim_lookup)
        assert "CLAIM REGISTRY" in msg
        assert len(registry) == 3  # c1, c2, c3

    def test_assigns_unique_ref_numbers(self) -> None:
        reviews = _make_theme_reviews()
        claim_lookup = _build_claim_lookup(_make_claims())
        registry, _msg = _build_message(reviews, claim_lookup)
        ref_numbers = list(registry.keys())
        assert len(ref_numbers) == len(set(ref_numbers))

    def test_reuses_ref_for_same_claim(self) -> None:
        # Duplicate c1 in two different theme reviews
        reviews = [
            {
                "theme_id": "t1",
                "label": "Theme A",
                "review": "Review A.",
                "key_claims": [
                    {"claim_id": "c1", "paper_id": "p1", "summary": "Claim 1."},
                ],
            },
            {
                "theme_id": "t2",
                "label": "Theme B",
                "review": "Review B.",
                "key_claims": [
                    {"claim_id": "c1", "paper_id": "p1", "summary": "Claim 1 again."},
                ],
            },
        ]
        claim_lookup = _build_claim_lookup(_make_claims())
        registry, _msg = _build_message(reviews, claim_lookup)
        assert len(registry) == 1  # c1 only once

    def test_includes_position_info(self) -> None:
        reviews = _make_theme_reviews()
        claim_lookup = _build_claim_lookup(_make_claims())
        _registry, msg = _build_message(reviews, claim_lookup)
        assert "p.2,§3" in msg  # c1's position
        assert "p.4,§1" in msg  # c2's position


class TestResolveCitations:
    def test_replaces_ref_with_position(self) -> None:
        sections = [
            ReviewSection(
                theme_id="t1",
                label="Chrono",
                content="Studies show regulation [1] and resetting [2].",
                citation_refs=[1, 2],
            ),
        ]
        citations = [
            ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1"),
            ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2"),
        ]
        claim_lookup = _build_claim_lookup(_make_claims())
        resolved = _resolve_citations(sections, citations, claim_lookup)
        assert '[1](cite:1 "p.2,§3")' in resolved[0].content
        assert '[2](cite:2 "p.4,§1")' in resolved[0].content

    def test_missing_claim_shows_fallback(self) -> None:
        sections = [
            ReviewSection(
                theme_id="t1",
                label="X",
                content="Unknown ref [99].",
                citation_refs=[99],
            ),
        ]
        citations = [
            ReviewCitation(ref_number=99, claim_id="nonexistent", paper_id="p1"),
        ]
        claim_lookup = _build_claim_lookup(_make_claims())
        resolved = _resolve_citations(sections, citations, claim_lookup)
        assert '[99](cite:99 "?")' in resolved[0].content

    def test_orphan_ref_left_intact(self) -> None:
        sections = [
            ReviewSection(
                theme_id="t1",
                label="X",
                content="Text with orphan [42].",
                citation_refs=[42],
            ),
        ]
        # No citation maps to [42]
        resolved = _resolve_citations(sections, [], _build_claim_lookup([]))
        assert "[42]" in resolved[0].content  # left as-is


class TestBuildReferences:
    def test_groups_by_paper(self) -> None:
        citations = [
            ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1"),
            ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2"),
            ReviewCitation(ref_number=3, claim_id="c3", paper_id="p1"),
        ]
        claim_lookup = _build_claim_lookup(_make_claims())
        paper_lookup = {p["paper_id"]: p for p in _make_papers()}
        refs = _build_references(citations, claim_lookup, paper_lookup)

        p1_ref = next(r for r in refs if r["paper_id"] == "p1")
        p2_ref = next(r for r in refs if r["paper_id"] == "p2")

        assert len(p1_ref["cited_in"]) == 2
        assert len(p2_ref["cited_in"]) == 1
        assert p1_ref["paper_title"] == "Circadian Metabolism Study"
        assert p1_ref["authors"] == ["Smith J", "Doe A"]

    def test_includes_position_data(self) -> None:
        citations = [
            ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1"),
        ]
        claim_lookup = _build_claim_lookup(_make_claims())
        paper_lookup = {p["paper_id"]: p for p in _make_papers()}
        refs = _build_references(citations, claim_lookup, paper_lookup)

        assert refs[0]["cited_in"][0]["page"] == 2
        assert refs[0]["cited_in"][0]["paragraph"] == 3


class TestCollectClaimIds:
    def test_maps_refs_to_claim_ids(self) -> None:
        citations = [
            ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1"),
            ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2"),
        ]
        ids = _collect_claim_ids([1, 2], citations)
        assert ids == ["c1", "c2"]

    def test_skips_unknown_refs(self) -> None:
        citations = [
            ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1"),
        ]
        ids = _collect_claim_ids([1, 99], citations)
        assert ids == ["c1"]


# --- Agent run tests ---


@dataclass
class FakeRunOutput:
    content: Any


def _make_aggregator_result() -> AggregatorResult:
    return AggregatorResult(
        title="Literature Review on Chronobiology and Gene Therapy",
        abstract="This review synthesizes findings from multiple studies.",
        sections=[
            ReviewSection(
                theme_id="t1",
                label="Chronobiology",
                content="Circadian regulation is well established [1]. Light plays a key role [2].",
                citation_refs=[1, 2],
            ),
            ReviewSection(
                theme_id="t2",
                label="Gene Therapy",
                content="AAV vectors demonstrate effective delivery [3].",
                citation_refs=[3],
            ),
        ],
        citations=[
            ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1"),
            ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2"),
            ReviewCitation(ref_number=3, claim_id="c3", paper_id="p1"),
        ],
    )


class TestAggregatorAgentRun:
    @pytest.fixture
    def input_data(self) -> dict[str, Any]:
        return {
            "theme_reviews": _make_theme_reviews(),
            "claims": _make_claims(),
            "papers": _make_papers(),
        }

    @pytest.fixture
    def mock_result(self) -> AggregatorResult:
        return _make_aggregator_result()

    async def test_run_returns_title_and_abstract(
        self, input_data: dict[str, Any], mock_result: AggregatorResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_result)

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run(input_data)

        assert result["title"] == mock_result.title
        assert result["abstract"] == mock_result.abstract

    async def test_run_returns_sections_with_resolved_citations(
        self, input_data: dict[str, Any], mock_result: AggregatorResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_result)

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run(input_data)

        sections = result["sections"]
        assert len(sections) == 2
        # Check [1] was resolved to [1](cite:1 "p.2,§3")
        assert '[1](cite:1 "p.2,§3")' in sections[0]["content"]
        assert '[2](cite:2 "p.4,§1")' in sections[0]["content"]
        assert '[3](cite:3 "p.5,§2")' in sections[1]["content"]

    async def test_run_returns_claim_ids_backward_compat(
        self, input_data: dict[str, Any], mock_result: AggregatorResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_result)

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run(input_data)

        assert result["sections"][0]["claim_ids"] == ["c1", "c2"]
        assert result["sections"][1]["claim_ids"] == ["c3"]

    async def test_run_returns_citations_with_positions(
        self, input_data: dict[str, Any], mock_result: AggregatorResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_result)

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run(input_data)

        citations = result["citations"]
        assert len(citations) == 3

        c1 = next(c for c in citations if c["claim_id"] == "c1")
        assert c1["page"] == 2
        assert c1["paragraph"] == 3
        assert c1["paper_title"] == "Circadian Metabolism Study"

    async def test_run_returns_references_grouped_by_paper(
        self, input_data: dict[str, Any], mock_result: AggregatorResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_result)

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run(input_data)

        refs = result["references"]
        assert len(refs) == 2  # p1 and p2

        p1_ref = next(r for r in refs if r["paper_id"] == "p1")
        assert len(p1_ref["cited_in"]) == 2  # c1 and c3 both from p1
        assert p1_ref["authors"] == ["Smith J", "Doe A"]

    async def test_run_passes_output_schema_to_agno(
        self, input_data: dict[str, Any], mock_result: AggregatorResult
    ) -> None:
        fake_output = FakeRunOutput(content=mock_result)

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        await agent.run(input_data)

        call_args = agent._agent.arun.call_args
        assert call_args[1]["output_schema"] is AggregatorResult

    async def test_run_handles_empty_claims(self) -> None:
        """Agent works with theme_reviews only (no claims/papers)."""
        minimal_result = AggregatorResult(
            title="Review",
            abstract="Summary.",
            sections=[
                ReviewSection(
                    theme_id="t1", label="Theme", content="No citations here.", citation_refs=[]
                ),
            ],
            citations=[],
        )
        fake_output = FakeRunOutput(content=minimal_result)

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        agent._agent = AsyncMock()
        agent._agent.arun = AsyncMock(return_value=fake_output)

        result = await agent.run({"theme_reviews": [{"theme_id": "t1", "label": "Theme", "review": "Text."}]})

        assert result["title"] == "Review"
        assert result["sections"][0]["claim_ids"] == []
        assert result["references"] == []
