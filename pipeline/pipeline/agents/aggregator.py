"""Aggregator agent: weaves theme reviews into a cohesive literature review with citations."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.parsing import run_agent_with_retry
from pipeline.agents.prompts.aggregator import AGGREGATOR_PROMPT

logger = logging.getLogger(__name__)

# --- Pydantic output models ---


class ReviewCitation(BaseModel):
    """A citation reference used in the review text."""

    ref_number: int
    claim_id: str
    paper_id: str


class ReviewSection(BaseModel):
    """One thematic section of the literature review."""

    theme_id: str
    label: str
    content: str = Field(min_length=1)
    citation_refs: list[int] = Field(default_factory=list)


class AggregatorResult(BaseModel):
    """Full literature review output from the LLM."""

    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)
    sections: list[ReviewSection] = Field(min_length=1)
    citations: list[ReviewCitation] = Field(default_factory=list)


# --- Agent ---


class AggregatorAgent:
    """Synthesizes all theme reviews into a cohesive literature review.

    Wraps an Agno agent internally but satisfies the pipeline Agent protocol.
    """

    def __init__(self) -> None:
        from pipeline.config import settings

        self._agent = AgnoAgent(
            name="Aggregator",
            model=create_model(),
            instructions=AGGREGATOR_PROMPT,
            output_schema=AggregatorResult,
            structured_outputs=True,
            debug_mode=settings.llm_debug_mode,
        )

    async def run(
        self,
        data: dict[str, Any],
        *,
        on_event: Callable[[Any], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        theme_reviews: list[dict[str, Any]] = data["theme_reviews"]
        claims: list[dict[str, Any]] = data.get("claims", [])
        papers: list[dict[str, Any]] = data.get("papers", [])

        # Build lookups for post-processing
        claim_lookup = _build_claim_lookup(claims)
        paper_lookup = {p["paper_id"]: p for p in papers}

        # Build numbered claim registry and LLM message
        claim_registry, message = _build_message(theme_reviews, claim_lookup)

        llm_result = await run_agent_with_retry(
            self._agent, message, AggregatorResult,
            context={
                "stage": "aggregation",
                "theme_count": len(theme_reviews),
            },
            on_event=on_event,
        )

        # Post-process: resolve [N] → [N](p.X,§Y) in section content
        resolved_sections = _resolve_citations(
            llm_result.sections, llm_result.citations, claim_lookup
        )

        # Build per-paper reference table
        references = _build_references(
            llm_result.citations, claim_lookup, paper_lookup
        )

        # Build output matching contract
        sections_out = []
        for section in resolved_sections:
            claim_ids = _collect_claim_ids(section.citation_refs, llm_result.citations)
            sections_out.append(
                {
                    "theme_id": section.theme_id,
                    "label": section.label,
                    "content": section.content,
                    "claim_ids": claim_ids,
                    "citation_refs": section.citation_refs,
                }
            )

        citations_out = [
            {
                "ref_number": c.ref_number,
                "claim_id": c.claim_id,
                "paper_id": c.paper_id,
                "paper_title": paper_lookup.get(c.paper_id, {}).get("title", ""),
                "page": claim_lookup.get(c.claim_id, {}).get("source", {}).get("page", 0),
                "paragraph": claim_lookup.get(c.claim_id, {}).get("source", {}).get("paragraph", 0),
            }
            for c in llm_result.citations
        ]

        return {
            "title": llm_result.title,
            "abstract": llm_result.abstract,
            "sections": sections_out,
            "citations": citations_out,
            "references": references,
        }


# --- Helpers ---


def _build_claim_lookup(claims: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build {claim_id: claim_dict} for position resolution."""
    return {c["id"]: c for c in claims if "id" in c}


def _build_message(
    theme_reviews: list[dict[str, Any]],
    claim_lookup: dict[str, dict[str, Any]],
) -> tuple[dict[int, str], str]:
    """Build LLM message with theme reviews and a numbered claim registry.

    Returns (claim_registry, message_text).
    claim_registry maps ref_number → claim_id.
    """
    ref_counter = 0
    claim_registry: dict[int, str] = {}
    claim_id_to_ref: dict[str, int] = {}

    lines: list[str] = []
    lines.append("=== THEME REVIEWS ===")
    lines.append("")

    for i, review in enumerate(theme_reviews, 1):
        label = review.get("label", review.get("theme_id", f"Theme {i}"))
        lines.append(f"--- THEME {i}: {label} ---")
        lines.append("")

        # Synthesis
        synthesis = review.get("review", "")
        if synthesis:
            lines.append(f"SYNTHESIS: {synthesis}")
            lines.append("")

        # Consensus
        consensus = review.get("consensus", [])
        if consensus:
            lines.append("CONSENSUS:")
            for point in consensus:
                lines.append(f"  - {point}")
            lines.append("")

        # Disagreements
        disagreements = review.get("disagreements", [])
        if disagreements:
            lines.append("DISAGREEMENTS:")
            for point in disagreements:
                lines.append(f"  - {point}")
            lines.append("")

        # Gaps
        gaps = review.get("gaps", [])
        if gaps:
            lines.append("GAPS:")
            for gap in gaps:
                lines.append(f"  - {gap}")
            lines.append("")

        # Key claims with ref numbers
        key_claims = review.get("key_claims", [])
        if key_claims:
            lines.append("KEY CLAIMS:")
            for kc in key_claims:
                cid = kc.get("claim_id", "")
                pid = kc.get("paper_id", "")
                summary = kc.get("summary", "")

                # Assign ref number (reuse if same claim cited in multiple themes)
                if cid in claim_id_to_ref:
                    ref = claim_id_to_ref[cid]
                else:
                    ref_counter += 1
                    ref = ref_counter
                    claim_id_to_ref[cid] = ref
                    claim_registry[ref] = cid

                # Add position info if available
                claim_data = claim_lookup.get(cid, {})
                source = claim_data.get("source", {})
                page = source.get("page", "?")
                para = source.get("paragraph", "?")

                lines.append(
                    f"  [{ref}] {summary} (paper: {pid}, p.{page},§{para})"
                )
            lines.append("")

    # Claim registry summary
    lines.append("=== CLAIM REGISTRY ===")
    lines.append("Use these [N] numbers for inline citations in your review.")
    lines.append("")
    for ref, cid in sorted(claim_registry.items()):
        pid = claim_id_to_ref_paper(cid, theme_reviews)
        lines.append(f"  [{ref}] claim_id={cid} paper_id={pid}")

    return claim_registry, "\n".join(lines)


def claim_id_to_ref_paper(claim_id: str, theme_reviews: list[dict[str, Any]]) -> str:
    """Find paper_id for a claim_id from theme reviews' key_claims."""
    for review in theme_reviews:
        for kc in review.get("key_claims", []):
            if kc.get("claim_id") == claim_id:
                return kc.get("paper_id", "unknown")
    return "unknown"


_REF_PATTERN = re.compile(r"\[(\d+)\]")


def _resolve_citations(
    sections: list[ReviewSection],
    citations: list[ReviewCitation],
    claim_lookup: dict[str, dict[str, Any]],
) -> list[ReviewSection]:
    """Replace [N] with [N](p.X,§Y) in section content using claim positions."""
    # Build ref_number → position mapping
    ref_to_pos: dict[int, str] = {}
    for cit in citations:
        claim = claim_lookup.get(cit.claim_id)
        if claim:
            source = claim.get("source", {})
            page = source.get("page", "?")
            para = source.get("paragraph", "?")
            ref_to_pos[cit.ref_number] = f"p.{page},§{para}"
        else:
            ref_to_pos[cit.ref_number] = "?"
            logger.warning(
                "Citation [%d] references unknown claim_id=%s", cit.ref_number, cit.claim_id
            )

    resolved = []
    for section in sections:
        content = section.content

        def replace_ref(match: re.Match) -> str:
            ref_num = int(match.group(1))
            pos = ref_to_pos.get(ref_num)
            if pos is not None:
                return f"[{ref_num}](cite:{ref_num} \"{pos}\")"
            logger.warning("Orphan reference [%d] in section %s", ref_num, section.theme_id)
            return match.group(0)  # leave as-is

        content = _REF_PATTERN.sub(replace_ref, content)
        resolved.append(
            ReviewSection(
                theme_id=section.theme_id,
                label=section.label,
                content=content,
                citation_refs=section.citation_refs,
            )
        )

    return resolved


def _build_references(
    citations: list[ReviewCitation],
    claim_lookup: dict[str, dict[str, Any]],
    paper_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build per-paper reference table aggregating all cited positions."""
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for cit in citations:
        claim = claim_lookup.get(cit.claim_id, {})
        source = claim.get("source", {})
        by_paper[cit.paper_id].append(
            {
                "ref_number": cit.ref_number,
                "page": source.get("page", 0),
                "paragraph": source.get("paragraph", 0),
            }
        )

    references = []
    for paper_id, cite_entries in by_paper.items():
        paper = paper_lookup.get(paper_id, {})
        references.append(
            {
                "paper_id": paper_id,
                "paper_title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "cited_in": [
                    {"ref_number": e["ref_number"], "page": e["page"], "paragraph": e["paragraph"]}
                    for e in cite_entries
                ],
            }
        )

    return references


def _collect_claim_ids(
    citation_refs: list[int], citations: list[ReviewCitation]
) -> list[str]:
    """Collect claim_ids for the given ref_numbers."""
    ref_to_claim = {c.ref_number: c.claim_id for c in citations}
    return [ref_to_claim[ref] for ref in citation_refs if ref in ref_to_claim]
