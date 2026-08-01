"""Tests for aggregator agent: helpers, citation resolution, and agent run."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.agents.aggregator import (
    _CITATION_RAIL_PATH,
    AggregatorAgent,
    AggregatorResult,
    ReviewCitation,
    ReviewSection,
    SectionBatchResult,
    TitleAbstractResult,
    _assign_ref_numbers,
    _build_batch_message,
    _build_claim_lookup,
    _build_references,
    _citation_guard,
    _collect_claim_ids,
    _enforce_citation_integrity,
    _find_orphan_refs,
    _merge_citations,
    _resolve_citations,
    _strip_invalid_citations,
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


class TestAssignRefNumbers:
    def test_assigns_unique_ref_numbers(self) -> None:
        reviews = _make_theme_reviews()
        ref_to_claim, claim_to_ref = _assign_ref_numbers(reviews)
        assert len(ref_to_claim) == 3  # c1, c2, c3
        ref_numbers = list(ref_to_claim.keys())
        assert len(ref_numbers) == len(set(ref_numbers))
        assert set(claim_to_ref) == {"c1", "c2", "c3"}

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
        ref_to_claim, claim_to_ref = _assign_ref_numbers(reviews)
        assert len(ref_to_claim) == 1  # c1 only once
        assert len(claim_to_ref) == 1


class TestBuildBatchMessage:
    def test_includes_all_theme_labels(self) -> None:
        reviews = _make_theme_reviews()
        claim_lookup = _build_claim_lookup(_make_claims())
        _ref_to_claim, claim_to_ref = _assign_ref_numbers(reviews)
        msg = _build_batch_message(reviews, claim_lookup, claim_to_ref)
        assert "Chronobiology" in msg
        assert "Gene Therapy" in msg

    def test_includes_claim_registry(self) -> None:
        reviews = _make_theme_reviews()
        claim_lookup = _build_claim_lookup(_make_claims())
        _ref_to_claim, claim_to_ref = _assign_ref_numbers(reviews)
        msg = _build_batch_message(reviews, claim_lookup, claim_to_ref)
        assert "CLAIM REGISTRY" in msg

    def test_scoped_to_given_batch_only(self) -> None:
        reviews = _make_theme_reviews()
        claim_lookup = _build_claim_lookup(_make_claims())
        _ref_to_claim, claim_to_ref = _assign_ref_numbers(reviews)
        # Only pass the first theme as the "batch"
        msg = _build_batch_message(reviews[:1], claim_lookup, claim_to_ref)
        assert "Chronobiology" in msg
        assert "Gene Therapy" not in msg

    def test_includes_position_info(self) -> None:
        reviews = _make_theme_reviews()
        claim_lookup = _build_claim_lookup(_make_claims())
        _ref_to_claim, claim_to_ref = _assign_ref_numbers(reviews)
        msg = _build_batch_message(reviews, claim_lookup, claim_to_ref)
        assert "p.2,§3" in msg  # c1's position
        assert "p.4,§1" in msg  # c2's position


class TestMergeCitations:
    def test_concats_citations_across_batches(self) -> None:
        batches = [
            SectionBatchResult(
                sections=[
                    ReviewSection(theme_id="t1", label="A", content="X [1].", citation_refs=[1])
                ],
                citations=[ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1")],
            ),
            SectionBatchResult(
                sections=[
                    ReviewSection(theme_id="t2", label="B", content="Y [2].", citation_refs=[2])
                ],
                citations=[ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2")],
            ),
        ]
        merged = _merge_citations(batches)
        assert {c.ref_number for c in merged} == {1, 2}

    def test_dedupes_shared_ref_number_keeps_first(self) -> None:
        shared = ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1")
        batches = [
            SectionBatchResult(
                sections=[
                    ReviewSection(theme_id="t1", label="A", content="X [1].", citation_refs=[1])
                ],
                citations=[shared],
            ),
            SectionBatchResult(
                sections=[
                    ReviewSection(theme_id="t2", label="B", content="Y [1].", citation_refs=[1])
                ],
                citations=[ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1")],
            ),
        ]
        merged = _merge_citations(batches)
        assert len(merged) == 1
        assert merged[0].ref_number == 1


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

    def test_orphan_ref_stripped_clean(self) -> None:
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
        assert "[42]" not in resolved[0].content
        assert resolved[0].content == "Text with orphan."

    def test_orphan_ref_strip_collapses_double_space(self) -> None:
        sections = [
            ReviewSection(
                theme_id="t1",
                label="X",
                content="Orphan claim [42] appears here too.",
                citation_refs=[42],
            ),
        ]
        resolved = _resolve_citations(sections, [], _build_claim_lookup([]))
        assert resolved[0].content == "Orphan claim appears here too."
        assert "  " not in resolved[0].content

    def test_orphan_ref_strip_before_comma(self) -> None:
        sections = [
            ReviewSection(
                theme_id="t1",
                label="X",
                content="Text [5], more text [5] again.",
                citation_refs=[5],
            ),
        ]
        resolved = _resolve_citations(sections, [], _build_claim_lookup([]))
        assert resolved[0].content == "Text, more text again."


class TestFindOrphanRefs:
    def test_no_orphans_returns_empty(self) -> None:
        sections = [
            ReviewSection(theme_id="t1", label="X", content="Text [1].", citation_refs=[1]),
        ]
        citations = [ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1")]
        assert _find_orphan_refs(sections, citations) == {}

    def test_single_orphan_flagged(self) -> None:
        sections = [
            ReviewSection(theme_id="t1", label="X", content="Text [42].", citation_refs=[42]),
        ]
        assert _find_orphan_refs(sections, []) == {"t1": [42]}

    def test_multiple_orphans_in_one_section_sorted(self) -> None:
        sections = [
            ReviewSection(
                theme_id="t1", label="X", content="Text [9] and [3].", citation_refs=[9, 3]
            ),
        ]
        assert _find_orphan_refs(sections, []) == {"t1": [3, 9]}

    def test_ref_resolved_by_different_batch_not_flagged(self) -> None:
        """Cross-batch reference: [1] appears in t1's content but its citation
        entry was emitted by whatever batch produced t2 — after global merge,
        it must NOT be a false positive (brief's OUT: pre-reconciliation
        per-section checking)."""
        sections = [
            ReviewSection(theme_id="t1", label="A", content="Cites [1].", citation_refs=[1]),
            ReviewSection(theme_id="t2", label="B", content="Own claim [2].", citation_refs=[2]),
        ]
        citations = [
            ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1"),
            ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2"),
        ]
        assert _find_orphan_refs(sections, citations) == {}


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


def _make_section_batch_result() -> SectionBatchResult:
    """Single-batch section result covering both fixture themes (default batch_size=5 → 1 batch)."""
    return SectionBatchResult(
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


def _make_title_abstract_result() -> TitleAbstractResult:
    return TitleAbstractResult(
        title="A Systematic Review of Circadian Regulation and Delivery Vectors",
        abstract="This review synthesizes findings from multiple studies.",
    )


def _make_aggregator_result() -> AggregatorResult:
    """Final assembled result (post batch-merge + reduce) for citation-Guard tests."""
    batch = _make_section_batch_result()
    title_abstract = _make_title_abstract_result()
    return AggregatorResult(
        title=title_abstract.title,
        abstract=title_abstract.abstract,
        sections=batch.sections,
        citations=batch.citations,
    )


def _run_agent_side_effect(section_result: SectionBatchResult, title_result: TitleAbstractResult):
    """Route mocked run_agent_with_retry calls to the right canned result by output_schema.

    Batch calls and the reduce call share one mocked entry point but request
    different schemas — dispatching on output_schema (rather than call order)
    keeps the test independent of asyncio.gather's scheduling order.
    """

    async def _side_effect(agent: Any, message: str, output_schema: type, **kwargs: Any) -> Any:
        if output_schema is SectionBatchResult:
            return section_result
        return title_result

    return _side_effect


class TestAggregatorAgentRun:
    @pytest.fixture
    def input_data(self) -> dict[str, Any]:
        return {
            "theme_reviews": _make_theme_reviews(),
            "claims": _make_claims(),
            "papers": _make_papers(),
        }

    @pytest.fixture
    def section_result(self) -> SectionBatchResult:
        return _make_section_batch_result()

    @pytest.fixture
    def title_result(self) -> TitleAbstractResult:
        return _make_title_abstract_result()

    async def test_run_returns_title_and_abstract(
        self,
        input_data: dict[str, Any],
        section_result: SectionBatchResult,
        title_result: TitleAbstractResult,
    ) -> None:
        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(input_data)

        assert result["title"] == title_result.title
        assert result["abstract"] == title_result.abstract

    async def test_run_returns_sections_with_resolved_citations(
        self,
        input_data: dict[str, Any],
        section_result: SectionBatchResult,
        title_result: TitleAbstractResult,
    ) -> None:
        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(input_data)

        sections = result["sections"]
        assert len(sections) == 2
        # Check [1] was resolved to [1](cite:1 "p.2,§3")
        assert '[1](cite:1 "p.2,§3")' in sections[0]["content"]
        assert '[2](cite:2 "p.4,§1")' in sections[0]["content"]
        assert '[3](cite:3 "p.5,§2")' in sections[1]["content"]

    async def test_run_returns_claim_ids_backward_compat(
        self,
        input_data: dict[str, Any],
        section_result: SectionBatchResult,
        title_result: TitleAbstractResult,
    ) -> None:
        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(input_data)

        assert result["sections"][0]["claim_ids"] == ["c1", "c2"]
        assert result["sections"][1]["claim_ids"] == ["c3"]

    async def test_run_returns_citations_with_positions(
        self,
        input_data: dict[str, Any],
        section_result: SectionBatchResult,
        title_result: TitleAbstractResult,
    ) -> None:
        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(input_data)

        citations = result["citations"]
        assert len(citations) == 3

        c1 = next(c for c in citations if c["claim_id"] == "c1")
        assert c1["page"] == 2
        assert c1["paragraph"] == 3
        assert c1["paper_title"] == "Circadian Metabolism Study"

    async def test_run_returns_references_grouped_by_paper(
        self,
        input_data: dict[str, Any],
        section_result: SectionBatchResult,
        title_result: TitleAbstractResult,
    ) -> None:
        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(input_data)

        refs = result["references"]
        assert len(refs) == 2  # p1 and p2

        p1_ref = next(r for r in refs if r["paper_id"] == "p1")
        assert len(p1_ref["cited_in"]) == 2  # c1 and c3 both from p1
        assert p1_ref["authors"] == ["Smith J", "Doe A"]

    async def test_run_passes_section_batch_result_schema(
        self,
        input_data: dict[str, Any],
        section_result: SectionBatchResult,
        title_result: TitleAbstractResult,
    ) -> None:
        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            await agent.run(input_data)

        schemas_used = {call.args[2] for call in mock_retry.call_args_list}
        assert schemas_used == {SectionBatchResult, TitleAbstractResult}

    async def test_run_handles_empty_claims(self) -> None:
        """Agent works with theme_reviews only (no claims/papers)."""
        minimal_section_result = SectionBatchResult(
            sections=[
                ReviewSection(
                    theme_id="t1", label="Theme", content="No citations here.", citation_refs=[]
                ),
            ],
            citations=[],
        )
        minimal_title_result = TitleAbstractResult(title="Review", abstract="Summary.")

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(
                minimal_section_result, minimal_title_result
            )
            result = await agent.run(
                {"theme_reviews": [{"theme_id": "t1", "label": "Theme", "review": "Text."}]}
            )

        assert result["title"] == "Review"
        assert result["sections"][0]["claim_ids"] == []
        assert result["references"] == []

    async def test_run_dispatches_one_batch_call_per_5_themes(
        self,
        section_result: SectionBatchResult,
        title_result: TitleAbstractResult,
    ) -> None:
        """6 themes with default batch_size=5 → 2 parallel batch calls + 1 reduce call."""
        reviews = [
            {"theme_id": f"t{i}", "label": f"Theme {i}", "review": f"Review {i}.", "key_claims": []}
            for i in range(1, 7)
        ]

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            await agent.run({"theme_reviews": reviews})

        batch_calls = [
            call for call in mock_retry.call_args_list if call.args[2] is SectionBatchResult
        ]
        reduce_calls = [
            call for call in mock_retry.call_args_list if call.args[2] is TitleAbstractResult
        ]
        assert len(batch_calls) == 2
        assert len(reduce_calls) == 1

    async def test_run_merges_sections_across_batches(self) -> None:
        """Merged output includes every theme's section, regardless of which batch produced it."""
        reviews = [
            {"theme_id": f"t{i}", "label": f"Theme {i}", "review": f"Review {i}.", "key_claims": []}
            for i in range(1, 7)
        ]

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        async def fake_process_batch(
            batch_idx: int,
            batch: list[dict[str, Any]],
            n_batches: int,
            claim_lookup: dict[str, Any],
            claim_to_ref: dict[str, int],
            on_event: Any,
        ) -> SectionBatchResult:
            return SectionBatchResult(
                sections=[
                    ReviewSection(
                        theme_id=t["theme_id"], label=t["label"], content="Text.", citation_refs=[]
                    )
                    for t in batch
                ],
                citations=[],
            )

        with (
            patch.object(
                AggregatorAgent,
                "_process_section_batch",
                new=AsyncMock(side_effect=fake_process_batch),
            ),
            patch.object(
                AggregatorAgent,
                "_run_title_abstract",
                new=AsyncMock(return_value=TitleAbstractResult(title="T", abstract="A.")),
            ),
        ):
            result = await agent.run({"theme_reviews": reviews})

        assert {s["theme_id"] for s in result["sections"]} == {f"t{i}" for i in range(1, 7)}
        assert len(result["sections"]) == 6


# --- orphan-ref reask tests ---


def _make_section_result_with_orphan() -> SectionBatchResult:
    """Same 2-theme batch as _make_section_batch_result, but t1's content
    additionally cites [2] with no matching citation entry."""
    return SectionBatchResult(
        sections=[
            ReviewSection(
                theme_id="t1",
                label="Chronobiology",
                content="Circadian regulation is well established [1]. Orphan claim [2] too.",
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
            ReviewCitation(ref_number=3, claim_id="c3", paper_id="p1"),
        ],
    )


class TestAggregatorReask:
    @pytest.fixture
    def input_data(self) -> dict[str, Any]:
        return {
            "theme_reviews": _make_theme_reviews(),
            "claims": _make_claims(),
            "papers": _make_papers(),
        }

    @pytest.fixture
    def title_result(self) -> TitleAbstractResult:
        return _make_title_abstract_result()

    async def test_no_reask_when_no_orphans(
        self,
        input_data: dict[str, Any],
        title_result: TitleAbstractResult,
    ) -> None:
        section_result = _make_section_batch_result()

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with (
            patch(
                "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
            ) as mock_retry,
            patch("pipeline.agents.aggregator.reask", new_callable=AsyncMock) as mock_reask,
        ):
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            await agent.run(input_data)

        mock_reask.assert_not_called()

    async def test_reask_fires_with_failure_description_naming_orphan(
        self,
        input_data: dict[str, Any],
        title_result: TitleAbstractResult,
    ) -> None:
        section_result = _make_section_result_with_orphan()
        corrected = _make_section_batch_result()  # fully resolved on reask

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with (
            patch(
                "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
            ) as mock_retry,
            patch("pipeline.agents.aggregator.reask", new_callable=AsyncMock) as mock_reask,
        ):
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            mock_reask.return_value = corrected
            result = await agent.run(input_data)

        mock_reask.assert_called_once()
        failure_description = mock_reask.call_args[0][2]
        assert "Chronobiology" in failure_description
        assert "[2]" in failure_description
        assert '[2](cite:2 "p.4,§1")' in result["sections"][0]["content"]

    async def test_one_reask_per_affected_batch_not_per_section(self) -> None:
        """A batch with multiple orphaned sections still gets exactly one reask call."""
        reviews = [
            {"theme_id": f"t{i}", "label": f"Theme {i}", "review": f"Review {i}.", "key_claims": []}
            for i in range(1, 7)  # 6 themes -> batch 1 (t1-t5), batch 2 (t6)
        ]

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        async def fake_process_batch(
            batch_idx: int,
            batch: list[dict[str, Any]],
            n_batches: int,
            claim_lookup: dict[str, Any],
            claim_to_ref: dict[str, int],
            on_event: Any,
        ) -> SectionBatchResult:
            if batch_idx == 1:
                # Every section in batch 1 cites an orphan ref, no citations at all.
                return SectionBatchResult(
                    sections=[
                        ReviewSection(
                            theme_id=t["theme_id"],
                            label=t["label"],
                            content="Text [99].",
                            citation_refs=[99],
                        )
                        for t in batch
                    ],
                    citations=[],
                )
            return SectionBatchResult(
                sections=[
                    ReviewSection(
                        theme_id=t["theme_id"],
                        label=t["label"],
                        content="Clean text.",
                        citation_refs=[],
                    )
                    for t in batch
                ],
                citations=[],
            )

        async def fake_reask(*args: Any, fallback: Any, **kwargs: Any) -> SectionBatchResult:
            return fallback()

        with (
            patch.object(
                AggregatorAgent,
                "_process_section_batch",
                new=AsyncMock(side_effect=fake_process_batch),
            ),
            patch.object(
                AggregatorAgent,
                "_run_title_abstract",
                new=AsyncMock(return_value=TitleAbstractResult(title="T", abstract="A.")),
            ),
            patch("pipeline.agents.aggregator.reask", new_callable=AsyncMock) as mock_reask,
        ):
            mock_reask.side_effect = fake_reask
            await agent.run({"theme_reviews": reviews})

        # 1 orphan-batch reask (task-1 layer) + 1 citation-integrity Guard reask
        # (this task's layer, post-merge): the batch reask's fallback leaves the
        # ref [99] still orphaned, so the Guard's own parse also fails and fires
        # its own reask via the same shared reask() helper.
        assert mock_reask.call_count == 2

    async def test_reask_exhaustion_falls_back_and_terminal_pass_strips_clean(
        self,
        input_data: dict[str, Any],
        title_result: TitleAbstractResult,
    ) -> None:
        section_result = _make_section_result_with_orphan()

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        async def fake_reask(*args: Any, fallback: Any, **kwargs: Any) -> SectionBatchResult:
            return fallback()  # simulate reask() exhaustion: unchanged, still orphaned

        with (
            patch(
                "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
            ) as mock_retry,
            patch("pipeline.agents.aggregator.reask", new_callable=AsyncMock) as mock_reask,
        ):
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            mock_reask.side_effect = fake_reask
            result = await agent.run(input_data)

        # Same double-layer as above: orphan-batch reask exhausts (still orphaned),
        # then the citation-integrity Guard's post-merge reask also exhausts,
        # falling through to strip-clean.
        assert mock_reask.call_count == 2
        content = result["sections"][0]["content"]
        assert "[2]" not in content
        assert '[1](cite:1 "p.2,§3")' in content


# --- output-side PII scrub tests ---


class TestOutputSidePiiScrub:
    """Test the §3.2 output-side PII scrub applied after citation resolution."""

    @pytest.fixture
    def title_result(self) -> TitleAbstractResult:
        return _make_title_abstract_result()

    async def test_section_content_person_redacted(self, title_result: TitleAbstractResult) -> None:
        """A PERSON name leaked into resolved section content is redacted."""
        section_result = SectionBatchResult(
            sections=[
                ReviewSection(
                    theme_id="t1",
                    label="Chronobiology",
                    content="A participant named Robert Chen disclosed personal details [1].",
                    citation_refs=[1],
                ),
            ],
            citations=[ReviewCitation(ref_number=1, claim_id="c1", paper_id="p1")],
        )

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(
                {
                    "theme_reviews": _make_theme_reviews(),
                    "claims": _make_claims(),
                    "papers": _make_papers(),
                }
            )

        content = result["sections"][0]["content"]
        assert "Robert Chen" not in content
        assert "[PERSON]" in content

    async def test_citation_marker_untouched_by_scrub(
        self, title_result: TitleAbstractResult
    ) -> None:
        """Scrubbing runs after citation resolution — [N](cite:...) markers survive intact."""
        section_result = _make_section_batch_result()

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(
                {
                    "theme_reviews": _make_theme_reviews(),
                    "claims": _make_claims(),
                    "papers": _make_papers(),
                }
            )

        assert '[1](cite:1 "p.2,§3")' in result["sections"][0]["content"]
        assert '[2](cite:2 "p.4,§1")' in result["sections"][0]["content"]

    async def test_title_and_abstract_scrubbed(self) -> None:
        """Reduce-pass title/abstract are re-scrubbed on the final assembled result."""
        section_result = SectionBatchResult(
            sections=[
                ReviewSection(
                    theme_id="t1", label="Theme", content="Clean content.", citation_refs=[]
                ),
            ],
            citations=[],
        )
        pii_title_result = TitleAbstractResult(
            title="Robert Chen's Review", abstract="Contact j.rodriguez@example.edu for details."
        )

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, pii_title_result)
            result = await agent.run({"theme_reviews": [{"theme_id": "t1", "label": "Theme"}]})

        assert "Robert Chen" not in result["title"]
        assert "[PERSON]" in result["title"]
        assert "j.rodriguez@example.edu" not in result["abstract"]
        assert "[EMAIL]" in result["abstract"]

    async def test_clean_title_abstract_unaffected(
        self, title_result: TitleAbstractResult
    ) -> None:
        """No PII in title/abstract → they pass through unchanged."""
        section_result = _make_section_batch_result()

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(
                {
                    "theme_reviews": _make_theme_reviews(),
                    "claims": _make_claims(),
                    "papers": _make_papers(),
                }
            )

        assert result["title"] == title_result.title
        assert result["abstract"] == title_result.abstract

    async def test_title_abstract_redaction_logged_without_pii_value(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Title/abstract redaction logs entity type + field, never the raw PII value."""
        section_result = SectionBatchResult(
            sections=[
                ReviewSection(
                    theme_id="t1", label="Theme", content="Clean content.", citation_refs=[]
                ),
            ],
            citations=[],
        )
        pii_title_result = TitleAbstractResult(
            title="Robert Chen's Review", abstract="Contact j.rodriguez@example.edu for details."
        )

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with (
            patch(
                "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
            ) as mock_retry,
            caplog.at_level("INFO", logger="pipeline.agents.aggregator"),
        ):
            mock_retry.side_effect = _run_agent_side_effect(section_result, pii_title_result)
            await agent.run({"theme_reviews": [{"theme_id": "t1", "label": "Theme"}]})

        reduce_logs = [
            r
            for r in caplog.records
            if "PII redacted (output-side)" in r.message and "stage=aggregation_reduce" in r.message
        ]
        assert len(reduce_logs) >= 1
        fields_logged = {r.message for r in reduce_logs}
        assert any("field=title" in m for m in fields_logged)
        assert any("field=abstract" in m for m in fields_logged)
        for record in reduce_logs:
            assert "Robert Chen" not in record.message
            assert "j.rodriguez@example.edu" not in record.message

    async def test_clean_section_content_unaffected(
        self, title_result: TitleAbstractResult
    ) -> None:
        """No PII present → section content passes through byte-for-byte."""
        section_result = _make_section_batch_result()

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with patch(
            "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            result = await agent.run(
                {
                    "theme_reviews": _make_theme_reviews(),
                    "claims": _make_claims(),
                    "papers": _make_papers(),
                }
            )

        assert "well established" in result["sections"][0]["content"]

    async def test_redaction_logged_without_pii_value(
        self, title_result: TitleAbstractResult, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Redaction is logged with entity type + theme_id, never the raw PII value."""
        section_result = SectionBatchResult(
            sections=[
                ReviewSection(
                    theme_id="t1",
                    label="Chronobiology",
                    content="A participant named Robert Chen disclosed personal details.",
                    citation_refs=[],
                ),
            ],
            citations=[],
        )

        with patch("pipeline.agents.aggregator.AgnoAgent"):
            agent = AggregatorAgent()

        with (
            patch(
                "pipeline.agents.aggregator.run_agent_with_retry", new_callable=AsyncMock
            ) as mock_retry,
            caplog.at_level("INFO", logger="pipeline.agents.aggregator"),
        ):
            mock_retry.side_effect = _run_agent_side_effect(section_result, title_result)
            await agent.run({"theme_reviews": [{"theme_id": "t1", "label": "Theme"}]})

        redaction_logs = [r for r in caplog.records if "PII redacted (output-side)" in r.message]
        assert len(redaction_logs) >= 1
        for record in redaction_logs:
            assert "Robert Chen" not in record.message
            assert "stage=aggregation" in record.message
            assert "theme_id=t1" in record.message


class TestCitationIntegrityGuard:
    """RAIL citation-integrity Guard: ref-resolves + claim_id-exists (§7.1)."""

    def test_rail_file_loads_without_error(self) -> None:
        assert _citation_guard is not None
        assert _CITATION_RAIL_PATH.exists()

    async def test_valid_result_passes_silently(self) -> None:
        claim_lookup = _build_claim_lookup(_make_claims())
        result = _make_aggregator_result()

        with patch("pipeline.agents.aggregator.reask", new_callable=AsyncMock) as mock_reask:
            out = await _enforce_citation_integrity(
                agent=None,
                llm_result=result,
                message="msg",
                claim_lookup=claim_lookup,
                on_event=None,
            )

        mock_reask.assert_not_called()
        assert out == result

    async def test_invalid_claim_id_triggers_reask(self) -> None:
        claim_lookup = _build_claim_lookup(_make_claims())
        bad_result = _make_aggregator_result().model_copy(
            update={
                "citations": [
                    ReviewCitation(ref_number=1, claim_id="does-not-exist", paper_id="p1"),
                    ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2"),
                    ReviewCitation(ref_number=3, claim_id="c3", paper_id="p1"),
                ]
            }
        )
        corrected_result = _make_aggregator_result()

        with patch("pipeline.agents.aggregator.reask", new_callable=AsyncMock) as mock_reask:
            mock_reask.return_value = corrected_result
            out = await _enforce_citation_integrity(
                agent=None,
                llm_result=bad_result,
                message="msg",
                claim_lookup=claim_lookup,
                on_event=None,
            )

        mock_reask.assert_called_once()
        failure_description = mock_reask.call_args.args[2]
        assert "does-not-exist" in failure_description
        assert out == corrected_result

    async def test_orphan_citation_ref_triggers_reask(self) -> None:
        claim_lookup = _build_claim_lookup(_make_claims())
        bad_result = _make_aggregator_result()
        bad_result.sections[0].citation_refs.append(99)  # no citations[].ref_number == 99
        corrected_result = _make_aggregator_result()

        with patch("pipeline.agents.aggregator.reask", new_callable=AsyncMock) as mock_reask:
            mock_reask.return_value = corrected_result
            out = await _enforce_citation_integrity(
                agent=None,
                llm_result=bad_result,
                message="msg",
                claim_lookup=claim_lookup,
                on_event=None,
            )

        mock_reask.assert_called_once()
        failure_description = mock_reask.call_args.args[2]
        assert "99" in failure_description
        assert out == corrected_result

    async def test_reask_exhausted_falls_back_to_strip_clean(self) -> None:
        claim_lookup = _build_claim_lookup(_make_claims())
        bad_result = _make_aggregator_result().model_copy(
            update={
                "citations": [
                    ReviewCitation(ref_number=1, claim_id="does-not-exist", paper_id="p1"),
                    ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2"),
                    ReviewCitation(ref_number=3, claim_id="c3", paper_id="p1"),
                ]
            }
        )

        with patch("pipeline.agents.aggregator.reask", new_callable=AsyncMock) as mock_reask:
            # reask() itself falls back on exhaustion and returns the still-invalid result
            mock_reask.return_value = bad_result
            out = await _enforce_citation_integrity(
                agent=None,
                llm_result=bad_result,
                message="msg",
                claim_lookup=claim_lookup,
                on_event=None,
            )

        assert [c.claim_id for c in out.citations] == ["c2", "c3"]
        assert 1 not in out.sections[0].citation_refs


class TestStripInvalidCitations:
    def test_valid_only_is_passthrough(self) -> None:
        claim_lookup = _build_claim_lookup(_make_claims())
        result = _make_aggregator_result()
        out = _strip_invalid_citations(result, claim_lookup)
        assert out == result

    def test_drops_invalid_claim_id(self) -> None:
        claim_lookup = _build_claim_lookup(_make_claims())
        result = _make_aggregator_result().model_copy(
            update={
                "citations": [
                    ReviewCitation(ref_number=1, claim_id="bogus", paper_id="p1"),
                    ReviewCitation(ref_number=2, claim_id="c2", paper_id="p2"),
                    ReviewCitation(ref_number=3, claim_id="c3", paper_id="p1"),
                ]
            }
        )
        out = _strip_invalid_citations(result, claim_lookup)
        assert [c.ref_number for c in out.citations] == [2, 3]
        assert 1 not in out.sections[0].citation_refs
        assert 2 in out.sections[0].citation_refs
