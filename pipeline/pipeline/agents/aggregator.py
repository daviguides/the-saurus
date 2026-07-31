"""Aggregator agent: weaves theme reviews into a cohesive literature review with citations."""

from __future__ import annotations

import asyncio
import logging
import re
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.parsing import reask, run_agent_with_retry
from pipeline.agents.prompts.aggregator import SECTION_BATCH_PROMPT, TITLE_ABSTRACT_PROMPT

logger = logging.getLogger(__name__)

# Themes per LLM call — balances quality vs call count (mirrors theme_reviewer.py)
BATCH_SIZE = 5

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
    """Full literature review output, merged from batch + reduce calls."""

    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)
    sections: list[ReviewSection] = Field(min_length=1)
    citations: list[ReviewCitation] = Field(default_factory=list)


class SectionBatchResult(BaseModel):
    """Structured output: sections + their citations for one batch of themes."""

    sections: list[ReviewSection] = Field(min_length=1)
    citations: list[ReviewCitation] = Field(default_factory=list)


class TitleAbstractResult(BaseModel):
    """Structured output: corpus-level title + abstract from assembled sections."""

    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)


# --- Agent ---


class AggregatorAgent:
    """Synthesizes all theme reviews into a cohesive literature review.

    Shards section generation into parallel batches of themes (mirroring
    theme_reviewer.py's BATCH_SIZE pattern), with a final reduce pass for
    title/abstract. Citation ref numbers are pre-assigned globally before
    any batch is dispatched, so parallel batches never collide.

    Wraps two Agno agents internally but satisfies the pipeline Agent protocol.
    """

    def __init__(self, batch_size: int = BATCH_SIZE) -> None:
        from pipeline.config import settings

        self._section_agent = AgnoAgent(
            name="AggregatorSection",
            model=create_model(),
            instructions=SECTION_BATCH_PROMPT,
            output_schema=SectionBatchResult,
            structured_outputs=True,
            debug_mode=settings.llm_debug_mode,
        )
        self._title_agent = AgnoAgent(
            name="AggregatorTitleAbstract",
            model=create_model(),
            instructions=TITLE_ABSTRACT_PROMPT,
            output_schema=TitleAbstractResult,
            structured_outputs=True,
            debug_mode=settings.llm_debug_mode,
        )
        self._batch_size = batch_size

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

        # Pre-assign global ref numbers before any batch is dispatched
        _ref_to_claim, claim_to_ref = _assign_ref_numbers(theme_reviews)

        batches = [
            theme_reviews[i : i + self._batch_size]
            for i in range(0, len(theme_reviews), self._batch_size)
        ]

        logger.info(
            "Aggregator: %d themes in %d batches (size %d)",
            len(theme_reviews),
            len(batches),
            self._batch_size,
        )

        batch_results = await asyncio.gather(
            *[
                self._process_section_batch(
                    idx, batch, len(batches), claim_lookup, claim_to_ref, on_event
                )
                for idx, batch in enumerate(batches, 1)
            ]
        )

        all_sections = [s for r in batch_results for s in r.sections]
        all_citations = _merge_citations(batch_results)

        orphans = _find_orphan_refs(all_sections, all_citations)
        if orphans:
            theme_to_batch_idx = {
                review.get("theme_id", ""): idx
                for idx, batch in enumerate(batches, 1)
                for review in batch
            }
            affected: dict[int, dict[str, list[int]]] = defaultdict(dict)
            for theme_id, refs in orphans.items():
                batch_idx = theme_to_batch_idx.get(theme_id)
                if batch_idx is not None:
                    affected[batch_idx][theme_id] = refs

            logger.info("Aggregator: %d batch(es) with orphan refs, reasking", len(affected))

            reasked_results = await asyncio.gather(
                *[
                    self._reask_orphaned_batch(
                        batch_idx,
                        batches[batch_idx - 1],
                        len(batches),
                        theme_orphans,
                        claim_lookup,
                        claim_to_ref,
                        batch_results[batch_idx - 1],
                        on_event,
                    )
                    for batch_idx, theme_orphans in affected.items()
                ]
            )
            for batch_idx, new_result in zip(affected.keys(), reasked_results, strict=True):
                batch_results[batch_idx - 1] = new_result

            all_sections = [s for r in batch_results for s in r.sections]
            all_citations = _merge_citations(batch_results)

        title_abstract = await self._run_title_abstract(all_sections, on_event)

        merged = AggregatorResult(
            title=title_abstract.title,
            abstract=title_abstract.abstract,
            sections=all_sections,
            citations=all_citations,
        )

        # Post-process: resolve [N] → [N](p.X,§Y) in section content
        resolved_sections = _resolve_citations(merged.sections, merged.citations, claim_lookup)

        # Build per-paper reference table
        references = _build_references(merged.citations, claim_lookup, paper_lookup)

        # Build output matching contract
        sections_out = []
        for section in resolved_sections:
            claim_ids = _collect_claim_ids(section.citation_refs, merged.citations)
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
            for c in merged.citations
        ]

        return {
            "title": merged.title,
            "abstract": merged.abstract,
            "sections": sections_out,
            "citations": citations_out,
            "references": references,
        }

    async def _process_section_batch(
        self,
        batch_idx: int,
        batch: list[dict[str, Any]],
        n_batches: int,
        claim_lookup: dict[str, dict[str, Any]],
        claim_to_ref: dict[str, int],
        on_event: Callable[[Any], Awaitable[None]] | None,
    ) -> SectionBatchResult:
        message = _build_batch_message(batch, claim_lookup, claim_to_ref)
        return await run_agent_with_retry(
            self._section_agent,
            message,
            SectionBatchResult,
            context={
                "stage": "aggregation",
                "batch": f"{batch_idx}/{n_batches}",
                "themes_in_batch": len(batch),
            },
            on_event=on_event,
        )

    async def _run_title_abstract(
        self,
        sections: list[ReviewSection],
        on_event: Callable[[Any], Awaitable[None]] | None,
    ) -> TitleAbstractResult:
        message = _build_title_abstract_message(sections)
        return await run_agent_with_retry(
            self._title_agent,
            message,
            TitleAbstractResult,
            context={"stage": "aggregation_reduce", "section_count": len(sections)},
            on_event=on_event,
        )

    async def _reask_orphaned_batch(
        self,
        batch_idx: int,
        batch: list[dict[str, Any]],
        n_batches: int,
        theme_orphans: dict[str, list[int]],
        claim_lookup: dict[str, dict[str, Any]],
        claim_to_ref: dict[str, int],
        original_result: SectionBatchResult,
        on_event: Callable[[Any], Awaitable[None]] | None,
    ) -> SectionBatchResult:
        """Reask a batch whose sections have post-reconciliation orphan refs.

        Rebuilds the batch's original message (pure function of its inputs —
        no caching needed) and appends one combined failure description
        naming every orphaned theme in the batch, mirroring
        theme_reviewer.py's invalid_by_theme reask pattern.
        """
        message = _build_batch_message(batch, claim_lookup, claim_to_ref)
        label_by_theme_id = {
            t.get("theme_id", ""): t.get("label", t.get("theme_id", "")) for t in batch
        }

        failure_description = "\n".join(
            f'For theme "{label_by_theme_id.get(theme_id, theme_id)}": reference(s) '
            f"{', '.join(f'[{n}]' for n in refs)} appear in your content but have no "
            f"matching entry in your citations list — for each, either add a citations "
            f"entry mapping it to a claim_id/paper_id from the claim registry, or "
            f"remove the marker from the text."
            for theme_id, refs in theme_orphans.items()
        )

        return await reask(
            self._section_agent,
            message,
            failure_description,
            SectionBatchResult,
            fallback=lambda: original_result,
            max_attempts=2,
            context={
                "stage": "aggregation",
                "batch": f"{batch_idx}/{n_batches}",
                "themes_in_batch": len(batch),
                "reask": "orphan_ref",
            },
            on_event=on_event,
        )


# --- Helpers ---


def _build_claim_lookup(claims: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build {claim_id: claim_dict} for position resolution."""
    return {c["id"]: c for c in claims if "id" in c}


def _assign_ref_numbers(
    theme_reviews: list[dict[str, Any]],
) -> tuple[dict[int, str], dict[str, int]]:
    """Walk every theme review's key_claims once, assign global sequential ref numbers.

    Reuses the ref if the same claim appears in multiple themes. Runs once,
    before any batch is dispatched, so parallel batches never collide on
    ref numbers.

    Returns (ref_to_claim, claim_to_ref).
    """
    ref_counter = 0
    ref_to_claim: dict[int, str] = {}
    claim_to_ref: dict[str, int] = {}

    for review in theme_reviews:
        for kc in review.get("key_claims", []):
            cid = kc.get("claim_id", "")
            if cid not in claim_to_ref:
                ref_counter += 1
                claim_to_ref[cid] = ref_counter
                ref_to_claim[ref_counter] = cid

    return ref_to_claim, claim_to_ref


def _build_batch_message(
    batch: list[dict[str, Any]],
    claim_lookup: dict[str, dict[str, Any]],
    claim_to_ref: dict[str, int],
) -> str:
    """Build LLM message for one batch of themes, scoped to their pre-assigned refs.

    Only includes the batch's own theme reviews and the claim registry
    entries relevant to them — bounds per-call input size regardless of
    total corpus size.
    """
    lines: list[str] = []
    lines.append("=== THEME REVIEWS ===")
    lines.append("")

    batch_registry: dict[int, tuple[str, str]] = {}  # ref -> (claim_id, paper_id)

    for i, review in enumerate(batch, 1):
        label = review.get("label", review.get("theme_id", f"Theme {i}"))
        lines.append(f"--- THEME {i}: {label} ---")
        lines.append("")

        synthesis = review.get("review", "")
        if synthesis:
            lines.append(f"SYNTHESIS: {synthesis}")
            lines.append("")

        consensus = review.get("consensus", [])
        if consensus:
            lines.append("CONSENSUS:")
            for point in consensus:
                lines.append(f"  - {point}")
            lines.append("")

        disagreements = review.get("disagreements", [])
        if disagreements:
            lines.append("DISAGREEMENTS:")
            for point in disagreements:
                lines.append(f"  - {point}")
            lines.append("")

        gaps = review.get("gaps", [])
        if gaps:
            lines.append("GAPS:")
            for gap in gaps:
                lines.append(f"  - {gap}")
            lines.append("")

        key_claims = review.get("key_claims", [])
        if key_claims:
            lines.append("KEY CLAIMS:")
            for kc in key_claims:
                cid = kc.get("claim_id", "")
                pid = kc.get("paper_id", "")
                summary = kc.get("summary", "")

                ref = claim_to_ref.get(cid)
                if ref is None:
                    continue
                batch_registry[ref] = (cid, pid)

                claim_data = claim_lookup.get(cid, {})
                source = claim_data.get("source", {})
                page = source.get("page", "?")
                para = source.get("paragraph", "?")

                lines.append(f"  [{ref}] {summary} (paper: {pid}, p.{page},§{para})")
            lines.append("")

        lines.append("")

    lines.append("=== CLAIM REGISTRY ===")
    lines.append("Use these [N] numbers for inline citations in your response.")
    lines.append("")
    for ref, (cid, pid) in sorted(batch_registry.items()):
        lines.append(f"  [{ref}] claim_id={cid} paper_id={pid}")

    return "\n".join(lines)


def _build_title_abstract_message(sections: list[ReviewSection]) -> str:
    """Build LLM message for the title/abstract reduce pass from assembled sections."""
    lines: list[str] = []
    lines.append("=== SECTIONS ===")
    lines.append("")

    for section in sections:
        lines.append(f"--- {section.label} ---")
        lines.append(section.content)
        lines.append("")

    return "\n".join(lines)


def _merge_citations(batch_results: list[SectionBatchResult]) -> list[ReviewCitation]:
    """Concat each batch's citations, deduping by ref_number (keep first).

    The same claim can be cited by themes in two different batches (both
    assigned the same ref number at pre-assignment time) — dedupe so the
    merged list has one entry per ref_number.
    """
    merged: dict[int, ReviewCitation] = {}
    for result in batch_results:
        for citation in result.citations:
            merged.setdefault(citation.ref_number, citation)
    return [merged[ref] for ref in sorted(merged)]


_REF_PATTERN = re.compile(r"\[(\d+)\]")


def _find_orphan_refs(
    sections: list[ReviewSection],
    citations: list[ReviewCitation],
) -> dict[str, list[int]]:
    """Find [N] refs in section content with no matching citation entry.

    Pure detection pass, run post-merge (against the FULL merged citation
    set) so a ref resolved by a different batch is never a false positive.
    Feeds the reask phase; _resolve_citations does the actual (terminal)
    strip-clean once reask has had its chance.
    """
    known_refs = {c.ref_number for c in citations}
    orphans: dict[str, list[int]] = {}
    for section in sections:
        missing = sorted({int(n) for n in _REF_PATTERN.findall(section.content)} - known_refs)
        if missing:
            orphans[section.theme_id] = missing
    return orphans


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
                return f'[{ref_num}](cite:{ref_num} "{pos}")'
            logger.warning(
                "Stripping unresolved orphan reference [%d] in section %s (reask exhausted)",
                ref_num,
                section.theme_id,
            )
            return ""  # strip-clean

        content = _REF_PATTERN.sub(replace_ref, content)
        content = re.sub(r"[ \t]{2,}", " ", content)  # collapse double-space from strip
        content = re.sub(r"[ \t]+([.,;:])", r"\1", content)  # strip space before punctuation
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


def _collect_claim_ids(citation_refs: list[int], citations: list[ReviewCitation]) -> list[str]:
    """Collect claim_ids for the given ref_numbers."""
    ref_to_claim = {c.ref_number: c.claim_id for c in citations}
    return [ref_to_claim[ref] for ref in citation_refs if ref in ref_to_claim]
