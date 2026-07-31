"""Theme reviewer agent: synthesizes claims across papers for batches of themes."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from agno.agent import Agent as AgnoAgent
from guardrails import Guard
from guardrails.validator_base import FailResult, PassResult, Validator, register_validator
from pydantic import BaseModel, Field

from pipeline.agents.models import create_model
from pipeline.agents.parsing import normalize_theme_name, reask, run_agent_with_retry
from pipeline.agents.prompts.theme_reviewer import THEME_REVIEWER_PROMPT

logger = logging.getLogger(__name__)

# Themes per LLM call — balances quality vs call count
BATCH_SIZE = 5

# --- Pydantic output models ---


@register_validator(name="claim-id-membership", data_type="string")
class ClaimIdMembership(Validator):
    """claim_id must be in this batch's valid_ids (supplied via validate() metadata).

    Fails closed: an absent `valid_ids` key in metadata is treated as an empty
    set, not a bypass.
    """

    def validate(self, value: str, metadata: dict) -> PassResult | FailResult:
        valid_ids = metadata.get("valid_ids", set())
        if value not in valid_ids:
            return FailResult(
                error_message=f"claim_id '{value}' is not in the valid set for this batch"
            )
        return PassResult()


class ReviewedClaim(BaseModel):
    """A claim referenced in the review, with its source."""

    claim_id: str = Field(json_schema_extra={"validators": [ClaimIdMembership(on_fail="reask")]})
    paper_id: str
    summary: str


class SingleThemeReview(BaseModel):
    """Review output for one theme within a batch."""

    theme_name: str
    synthesis: str = Field(min_length=1)
    consensus: list[str] = Field(min_length=1)
    disagreements: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    key_claims: list[ReviewedClaim] = Field(default_factory=list)


class BatchThemeReviewResult(BaseModel):
    """Structured output: reviews for multiple themes in one call."""

    reviews: list[SingleThemeReview] = Field(min_length=1)


# Built once at import time: Guard.for_pydantic reads validators off the class
# definition, which doesn't change per call — only the `metadata` passed to
# .validate() (namely valid_ids) varies per batch.
_claim_id_guard = Guard.for_pydantic(BatchThemeReviewResult)


def _build_claim_id_failure_description(guard: Guard, result: BatchThemeReviewResult) -> str:
    """Reproduce the per-theme claim_id failure message from Guard's reask list.

    Must be called synchronously, immediately after `guard.validate(...)`, with
    no `await` in between — `guard.history.last` is shared mutable state on a
    module-level Guard reused across batches gathered concurrently.
    """
    reasks = guard.history.last.iterations[-1].outputs.reasks
    bad_ids_by_theme_idx: dict[int, list[str]] = defaultdict(list)
    for field_reask in reasks:
        theme_idx = field_reask.path[1]
        bad_ids_by_theme_idx[theme_idx].append(field_reask.incorrect_value)

    return "\n".join(
        f'For theme "{result.reviews[idx].theme_name}": claim_id '
        f"{', '.join(ids)} {'is' if len(ids) == 1 else 'are'} not in the valid set "
        f"for this batch — provide valid claim_ids or omit these entries."
        for idx, ids in bad_ids_by_theme_idx.items()
    )


# --- Agent ---


class ThemeReviewerAgent:
    """Synthesizes claims across papers for canonical themes.

    Processes themes in batches (default 5 per call) to balance
    LLM attention quality vs call count.
    """

    def __init__(self, batch_size: int = BATCH_SIZE) -> None:
        from pipeline.config import settings

        self._agent = AgnoAgent(
            name="ThemeReviewer",
            model=create_model(),
            instructions=THEME_REVIEWER_PROMPT,
            output_schema=BatchThemeReviewResult,
            structured_outputs=True,
            debug_mode=settings.llm_debug_mode,
        )
        self._batch_size = batch_size

    async def run_batch(
        self,
        themes: list[dict[str, Any]],
        all_claims: list[dict[str, Any]],
        *,
        on_event: Callable[[Any], Awaitable[None]] | None = None,
    ) -> list[dict[str, Any]]:
        """Process all themes in batches, return list of review dicts."""
        # Build claim index by theme_id
        claims_by_theme_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for claim in all_claims:
            tid = claim.get("theme_id", "")
            claims_by_theme_id[tid].append(claim)

        # Chunk themes into batches
        batches = [
            themes[i : i + self._batch_size] for i in range(0, len(themes), self._batch_size)
        ]

        logger.info(
            "ThemeReviewer: %d themes in %d batches (size %d)",
            len(themes),
            len(batches),
            self._batch_size,
        )

        async def _process_batch(
            batch_idx: int, batch: list[dict[str, Any]]
        ) -> list[dict[str, Any]]:
            # Collect relevant claims for this batch
            batch_claims: dict[str, list[dict[str, Any]]] = {}
            for theme in batch:
                source_ids = set(theme.get("source_theme_ids", []))
                if source_ids:
                    relevant = [c for c in all_claims if c.get("theme_id") in source_ids]
                else:
                    relevant = claims_by_theme_id.get(theme["id"], [])
                batch_claims[theme["id"]] = relevant

            message = _build_batch_message(batch, batch_claims)

            result = await run_agent_with_retry(
                self._agent,
                message,
                BatchThemeReviewResult,
                context={
                    "stage": "theme_review",
                    "batch": f"{batch_idx}/{len(batches)}",
                    "themes_in_batch": len(batch),
                    "total_claims": sum(len(v) for v in batch_claims.values()),
                },
                on_event=on_event,
            )

            valid_ids = set()
            for claims_list in batch_claims.values():
                for c in claims_list:
                    valid_ids.add(c.get("id", ""))

            # Guard.validate() is synchronous and does no I/O — it runs to
            # completion within this coroutine's turn, so no other
            # concurrently-gathered batch's call can interleave with it. The
            # failure-description build below must stay synchronous too (see
            # _build_claim_id_failure_description docstring).
            guard_outcome = _claim_id_guard.validate(
                result.model_dump_json(), metadata={"valid_ids": valid_ids}
            )

            if not guard_outcome.validation_passed:
                failure_description = _build_claim_id_failure_description(_claim_id_guard, result)
                logger.warning(
                    "ThemeReviewer batch %d: invalid claim_ids detected, reasking",
                    batch_idx,
                )
                original_result = result
                result = await reask(
                    self._agent,
                    message,
                    failure_description,
                    BatchThemeReviewResult,
                    fallback=lambda: original_result,
                    max_attempts=2,
                    context={
                        "stage": "theme_review",
                        "batch": f"{batch_idx}/{len(batches)}",
                        "themes_in_batch": len(batch),
                        "total_claims": sum(len(v) for v in batch_claims.values()),
                        "reask": "valid_ids",
                    },
                    on_event=on_event,
                )

            # Map results back to theme IDs
            # B4: Normalize theme names more aggressively for matching
            theme_name_to_id = {normalize_theme_name(t.get("name", "")): t["id"] for t in batch}
            theme_name_to_meta = {normalize_theme_name(t.get("name", "")): t for t in batch}

            def _find_theme(review_name: str) -> tuple[str, dict[str, Any]]:
                """Find matching theme by exact or substring match."""
                key = normalize_theme_name(review_name)
                # Exact match
                if key in theme_name_to_id:
                    return theme_name_to_id[key], theme_name_to_meta[key]
                # Substring/contains match
                for canon_name, tid in theme_name_to_id.items():
                    if key in canon_name or canon_name in key:
                        return tid, theme_name_to_meta[canon_name]
                return "", {}

            miss_names = [
                review.theme_name
                for review in result.reviews
                if not _find_theme(review.theme_name)[0]
            ]

            if miss_names:
                valid_names = ", ".join(t.get("name", "") for t in batch)
                failure_description = (
                    f"The following theme_name value(s) did not match any theme "
                    f"in this batch: {', '.join(miss_names)}. "
                    f"Valid theme names for this batch are: {valid_names}. "
                    f"Use one of these exact names for theme_name in your response."
                )
                original_result = result
                result = await reask(
                    self._agent,
                    message,
                    failure_description,
                    BatchThemeReviewResult,
                    fallback=lambda: original_result,
                    context={
                        "stage": "theme_review",
                        "batch": f"{batch_idx}/{len(batches)}",
                        "themes_in_batch": len(batch),
                        "reask": "theme_name_mismatch",
                    },
                    on_event=on_event,
                )

            batch_reviews: list[dict[str, Any]] = []
            for review in result.reviews:
                theme_id, theme_meta = _find_theme(review.theme_name)

                # Validate claim IDs (worst case: same silent filter as before reask)
                validated_claims = [kc for kc in review.key_claims if kc.claim_id in valid_ids]

                batch_reviews.append(
                    {
                        "theme_id": theme_id or review.theme_name,
                        "label": theme_meta.get("name", review.theme_name),
                        "review": review.synthesis,
                        "consensus": review.consensus,
                        "disagreements": review.disagreements,
                        "gaps": review.gaps,
                        "claim_ids": [kc.claim_id for kc in validated_claims],
                        "key_claims": [kc.model_dump() for kc in validated_claims],
                    }
                )
            return batch_reviews

        nested = await asyncio.gather(
            *[_process_batch(idx, batch) for idx, batch in enumerate(batches, 1)]
        )
        return [review for batch_reviews in nested for review in batch_reviews]


def _build_batch_message(
    themes: list[dict[str, Any]],
    claims_per_theme: dict[str, list[dict[str, Any]]],
) -> str:
    """Build LLM message with multiple themes and their claims."""
    lines: list[str] = []
    lines.append(f"Analyze the following {len(themes)} themes:\n")

    for theme in themes:
        name = theme.get("name", theme.get("label", "Unknown"))
        desc = theme.get("description", "")
        aliases = ", ".join(theme.get("aliases", []))
        theme_id = theme["id"]

        lines.append(f'<theme id="{theme_id}" name="{name}">')
        lines.append(f"DESCRIPTION: {desc}")
        if aliases:
            lines.append(f"ALIASES: {aliases}")

        # Group claims by paper
        claims = claims_per_theme.get(theme_id, [])
        by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for claim in claims:
            pid = claim.get("source", {}).get("paper_id", "unknown")
            by_paper[pid].append(claim)

        lines.append(f"PAPERS: {len(by_paper)} paper(s), {len(claims)} claims")
        lines.append("")

        for pid, paper_claims in by_paper.items():
            lines.append(f"  Paper: {pid}")
            for claim in paper_claims:
                cid = claim.get("id", "?")
                summary = claim.get("summary", claim.get("text", ""))
                page = claim.get("page", claim.get("source", {}).get("page", "?"))
                para = claim.get("paragraph", claim.get("source", {}).get("paragraph", "?"))
                deep = claim.get("deep", "")
                lines.append(
                    f'  <claim id="{cid}" paper="{pid}" page="{page}" '
                    f'paragraph="{para}">{summary}</claim>'
                )
                if deep:
                    lines.append(f"      Context: {deep[:300]}")
            lines.append("")

        lines.append("</theme>")
        lines.append("")

    return "\n".join(lines)
