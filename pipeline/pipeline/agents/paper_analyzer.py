"""Paper analyzer agent: extracts themes AND claims in a single pass."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel, Field

from pipeline.agents.gate import evaluate_topic_gate
from pipeline.agents.models import create_model
from pipeline.agents.parsing import normalize_theme_name, reask, run_agent_with_retry
from pipeline.agents.prompts.paper_analyzer import PAPER_ANALYZER_PROMPT
from pipeline.core.embedding import cosine_similarity, embed_batch
from pipeline.core.exceptions import TopicGateRejectedError
from pipeline.core.tokens import count_tokens

logger = logging.getLogger(__name__)

# --- Pydantic output models ---


class ClaimPosition(BaseModel):
    """A location in the paper where a claim appears."""

    page: int
    paragraph: int


class ExtractedClaim(BaseModel):
    """A single claim extracted from a paper."""

    text: str
    position: ClaimPosition
    deep: str
    summary: str


class ThemeWithClaims(BaseModel):
    """A theme with its associated claims — extracted together in one pass."""

    name: str
    description: str
    positions: list[ClaimPosition] = Field(min_length=1)
    claims: list[ExtractedClaim] = Field(min_length=1)


class PaperAnalysisResult(BaseModel):
    """Structured output: themes + claims extracted from a single paper."""

    themes: list[ThemeWithClaims] = Field(min_length=1)


# --- Context window budget ---


async def _pack_under_budget(content: str, budget: int) -> list[str]:
    """Greedily pack content's blank-line-separated paragraph blocks into
    sub-chunks that stay under budget tokens, without splitting a paragraph
    mid-block.

    A single block that alone exceeds budget is forwarded as its own
    oversized sub-chunk (best-effort) rather than truncated — silent
    truncation is itself a grounding hazard (design-doc §4.1).
    """
    blocks = [b for b in content.split("\n\n") if b.strip()]
    if not blocks:
        return [content]

    block_tokens = await asyncio.gather(*(count_tokens(b) for b in blocks))

    sub_chunks: list[str] = []
    current_blocks: list[str] = []
    current_tokens = 0

    for block, tokens in zip(blocks, block_tokens, strict=True):
        if tokens > budget:
            logger.warning(
                "Paragraph block exceeds token budget alone (%d > %d); "
                "forwarding as its own sub-chunk",
                tokens,
                budget,
            )
        if current_blocks and current_tokens + tokens > budget:
            sub_chunks.append("\n\n".join(current_blocks))
            current_blocks = []
            current_tokens = 0
        current_blocks.append(block)
        current_tokens += tokens

    if current_blocks:
        sub_chunks.append("\n\n".join(current_blocks))

    return sub_chunks


# --- Provenance grounding (f-007/f-016): claim.text vs claim.deep ---


async def _grounding_scores(claims: list[ExtractedClaim]) -> list[float]:
    """Cosine similarity between each claim.text and its own claim.deep.

    Batched into a single embed_batch call (claim texts then deep texts, same
    order) rather than one embed_text call per claim per field.
    """
    if not claims:
        return []
    texts = [c.text for c in claims] + [c.deep for c in claims]
    vectors = await embed_batch(texts)
    n = len(claims)
    return [cosine_similarity(vectors[i], vectors[n + i]) for i in range(n)]


def _build_grounding_failure_description(
    flagged: list[tuple[str, ExtractedClaim, float]],
    threshold: float,
) -> str:
    """One combined failure description covering every flagged claim in the
    paper — mirrors theme_reviewer's invalid_by_theme/miss_names pattern of a
    single reask call per batch, not one reask per item."""
    lines = [
        f'- theme "{theme_name}", position [p.{c.position.page},§{c.position.paragraph}]: '
        f'claim "{c.text}" is not well-supported by its own "deep" excerpt '
        f'"{c.deep}" (similarity {score:.2f} < required {threshold:.2f})'
        for theme_name, c, score in flagged
    ]
    return (
        "The following claims are not sufficiently grounded in their own 'deep' "
        "source paragraph. For each: either correct 'deep' so it verbatim-contains "
        "the claim, or correct 'text' so it accurately reflects what 'deep' says. "
        "Do not invent a new claim.\n" + "\n".join(lines)
    )


async def _drop_ungrounded(
    analysis: PaperAnalysisResult,
    threshold: float,
    paper_id: str,
) -> PaperAnalysisResult:
    """Recompute grounding scores and remove any claim still below threshold.

    Uses model_copy(update=...) rather than reconstructing ThemeWithClaims/
    PaperAnalysisResult via the constructor: model_copy does not re-run
    min_length=1 validation on the updated field, so a theme legitimately
    ending up with zero claims after a drop doesn't raise — the theme is kept
    (claims_out simply has none for it), consistent with existing downstream
    code tolerating arbitrary claims_out contents.
    """
    new_themes = []
    for theme in analysis.themes:
        scores = await _grounding_scores(theme.claims)
        kept = []
        for claim, score in zip(theme.claims, scores, strict=True):
            if score < threshold:
                logger.warning(
                    "Provenance check dropped claim: paper_id=%s theme=%s "
                    "position=[p.%d,§%d] score=%.3f threshold=%.3f",
                    paper_id,
                    theme.name,
                    claim.position.page,
                    claim.position.paragraph,
                    score,
                    threshold,
                )
                continue
            kept.append(claim)
        new_themes.append(theme.model_copy(update={"claims": kept}))
    return analysis.model_copy(update={"themes": new_themes})


# --- Agent ---


class PaperAnalyzerAgent:
    """Extracts themes and claims from a single paper in one LLM pass.

    The LLM reads the paper once and produces themes with their claims
    co-located, avoiding redundant re-reading of the paper.
    """

    def __init__(self) -> None:
        from pipeline.config import settings

        self._agent = AgnoAgent(
            name="PaperAnalyzer",
            model=create_model(),
            instructions=PAPER_ANALYZER_PROMPT,
            output_schema=PaperAnalysisResult,
            structured_outputs=True,
            debug_mode=settings.llm_debug_mode,
        )

    async def _enforce_provenance(
        self,
        analysis: PaperAnalysisResult,
        message: str,
        paper_id: str,
        *,
        on_event: Callable[[Any], Awaitable[None]] | None,
    ) -> PaperAnalysisResult:
        """Flag claims not cosine-supported by their own deep excerpt, reask
        once (combined failure description for the whole paper), then drop
        anything still ungrounded after the reask attempt."""
        from pipeline.config import settings

        threshold = settings.provenance_similarity_threshold
        flagged: list[tuple[str, ExtractedClaim, float]] = []
        for theme in analysis.themes:
            scores = await _grounding_scores(theme.claims)
            for claim, score in zip(theme.claims, scores, strict=True):
                if score < threshold:
                    flagged.append((theme.name, claim, score))
                    logger.info(
                        "Provenance check flagged claim: paper_id=%s theme=%s "
                        "position=[p.%d,§%d] score=%.3f threshold=%.3f",
                        paper_id,
                        theme.name,
                        claim.position.page,
                        claim.position.paragraph,
                        score,
                        threshold,
                    )

        if not flagged:
            return analysis

        failure_description = _build_grounding_failure_description(flagged, threshold)

        corrected = await reask(
            self._agent,
            message,
            failure_description,
            PaperAnalysisResult,
            fallback=lambda: analysis,
            max_attempts=2,
            context={
                "paper_id": paper_id,
                "stage": "paper_analysis",
                "reask": "provenance_grounding",
            },
            on_event=on_event,
        )

        return await _drop_ungrounded(corrected, threshold, paper_id)

    async def run(
        self,
        data: dict[str, Any],
        *,
        on_event: Callable[[Any], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        from pipeline.config import settings

        paper_id = data["paper_id"]
        content = data["content"]

        gate_result = await evaluate_topic_gate(
            content=content,
            page_count=data.get("page_count", 0),
            title=data.get("title", ""),
            authors=data.get("authors", []),
        )
        if gate_result.verdict == "reject":
            raise TopicGateRejectedError(
                f"Paper {paper_id} rejected by topic gate: {gate_result.reason}",
                reason=gate_result.reason or "topic gate rejected",
            )

        context = {
            "paper_id": paper_id,
            "paper_title": data.get("title", ""),
            "stage": "paper_analysis",
        }

        # CWM (§4.1): measure instructions + content together, act on the
        # result — not the count-then-log-only pattern run_agent_with_retry
        # uses for every caller (this agent's chunking fallback is not
        # shared, so the enforcement lives here, not in the shared retry
        # loop).
        prompt_tokens = await count_tokens(PAPER_ANALYZER_PROMPT)
        content_tokens = await count_tokens(content)
        budget = settings.chunk_token_threshold

        if prompt_tokens + content_tokens <= budget:
            analysis = await run_agent_with_retry(
                self._agent,
                content,
                PaperAnalysisResult,
                context=context,
                on_event=on_event,
            )
            analysis = await self._enforce_provenance(
                analysis,
                content,
                paper_id,
                on_event=on_event,
            )
            themes_out, claims_out = self._split_analysis(analysis, paper_id)
        else:
            logger.warning(
                "Paper %s over token budget (%d > %d), splitting into sub-chunks",
                paper_id,
                prompt_tokens + content_tokens,
                budget,
            )
            sub_chunks = await _pack_under_budget(
                content,
                max(budget - prompt_tokens, 1),
            )
            chunk_results: list[dict[str, Any]] = []
            for i, sub_content in enumerate(sub_chunks):
                sub_analysis = await run_agent_with_retry(
                    self._agent,
                    sub_content,
                    PaperAnalysisResult,
                    context={**context, "sub_chunk": i},
                    on_event=on_event,
                )
                sub_analysis = await self._enforce_provenance(
                    sub_analysis,
                    sub_content,
                    paper_id,
                    on_event=on_event,
                )
                sub_themes, sub_claims = self._split_analysis(sub_analysis, paper_id)
                chunk_results.append({"themes": sub_themes, "claims": sub_claims})
            merged = merge_chunk_results(chunk_results)
            themes_out, claims_out = merged["themes"], merged["claims"]

        return {
            "themes": themes_out,
            "claims": claims_out,
        }

    def _split_analysis(
        self,
        analysis: PaperAnalysisResult,
        paper_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Split a PaperAnalysisResult into separate themes and claims dicts
        (maintains compatibility with downstream stages)."""
        themes_out: list[dict[str, Any]] = []
        claims_out: list[dict[str, Any]] = []

        for theme in analysis.themes:
            theme_id = str(uuid4())
            themes_out.append(
                {
                    "id": theme_id,
                    "name": theme.name,
                    "description": theme.description,
                    "paper_id": paper_id,
                    "positions": [p.model_dump() for p in theme.positions],
                }
            )

            for claim in theme.claims:
                claims_out.append(
                    {
                        "id": str(uuid4()),
                        "theme_id": theme_id,
                        "theme_name": theme.name,
                        "text": claim.text,
                        "page": claim.position.page,
                        "paragraph": claim.position.paragraph,
                        "deep": claim.deep,
                        "summary": claim.summary,
                        "source": {
                            "paper_id": paper_id,
                            "page": claim.position.page,
                            "paragraph": claim.position.paragraph,
                        },
                    }
                )

        return themes_out, claims_out


def merge_chunk_results(chunk_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge per-chunk PaperAnalyzerAgent outputs into one paper-level result.

    Reconciles the same theme found in different chunks by exact normalized
    name match (no substring/fuzzy fallback — chunk-merge clusters unknowns
    against unknowns, unlike theme_reviewer's match against a small known
    candidate set, so a fuzzy match risks merging genuinely distinct themes).
    The first chunk to produce a given theme name keeps its id as canonical;
    later occurrences contribute only their positions. Claims are remapped
    to the canonical theme_id and concatenated.
    """
    themes_by_key: dict[str, dict[str, Any]] = {}
    theme_id_remap: dict[str, str] = {}

    for chunk in chunk_results:
        for theme in chunk.get("themes", []):
            key = normalize_theme_name(theme.get("name", ""))
            canonical = themes_by_key.get(key)
            if canonical is None:
                canonical = dict(theme)
                canonical["positions"] = list(theme.get("positions", []))
                themes_by_key[key] = canonical
            else:
                for position in theme.get("positions", []):
                    if position not in canonical["positions"]:
                        canonical["positions"].append(position)
            theme_id_remap[theme["id"]] = canonical["id"]

    merged_claims: list[dict[str, Any]] = []
    for chunk in chunk_results:
        for claim in chunk.get("claims", []):
            merged_claim = dict(claim)
            merged_claim["theme_id"] = theme_id_remap.get(claim["theme_id"], claim["theme_id"])
            merged_claims.append(merged_claim)

    return {
        "themes": list(themes_by_key.values()),
        "claims": merged_claims,
    }
