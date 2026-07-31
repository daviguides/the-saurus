"""Pipeline orchestrator: runs stages in order with parallel execution and sync barriers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeline.agents import (
    AggregatorAgent,
    PaperAnalyzerAgent,
    ThemeDedupAgent,
    ThemeReviewerAgent,
    merge_chunk_results,
)
from pipeline.agents.event_bridge import create_agent_event_callback
from pipeline.agents.judge_gate import score_review
from pipeline.agents.protocol import Agent
from pipeline.agents.toxic_gate import check_toxicity
from pipeline.core import (
    EventEmitter,
    EventType,
    JobState,
    JobStatus,
    PaperEntry,
<<<<<<< HEAD
    TopicGateRejectedError,
=======
    cluster_themes,
>>>>>>> 13169dd (feat(pipeline): shard theme dedup into cluster-map-reconcile)
    quarantine_job,
    read_yaml,
    reconcile_canonical_themes,
    write_status,
    write_yaml,
)
from pipeline.core.persistence import release_lock
from pipeline.core.qdrant import QdrantIndexer, get_indexer
from pipeline.ws.stream import get_or_create_emitter, remove_emitter

from .progress import ProgressTracker
from .stages import Stage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inter-stage typed models
# ---------------------------------------------------------------------------

AnalysisResults = list[tuple[PaperEntry, dict[str, Any]]]
"""Per-paper analysis output: list of (paper, {themes, claims}) pairs."""

DedupResult = dict[str, Any]
"""Theme dedup output: {theme_map, themes}."""

ReviewResults = list[dict[str, Any]]
"""Per-theme review output: list of review dicts."""


@dataclass
class PipelineContext:
    """Shared state threaded through all pipeline stages."""

    job_id: str
    job_path: Path
    jobs_dir: Path
    papers: list[PaperEntry]
    paper_contents: dict[str, list[str]]
    emitter: EventEmitter
    tracker: ProgressTracker
    indexer: QdrantIndexer | None
    qdrant_tasks: set[asyncio.Task] = field(default_factory=set)

    def fire_qdrant(self, coro: Coroutine, *, operation: str = "write") -> None:
        """Schedule a Qdrant write as fire-and-forget background task."""
        task = asyncio.create_task(_safe_qdrant(coro, operation=operation))
        self.qdrant_tasks.add(task)
        task.add_done_callback(self.qdrant_tasks.discard)


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------


async def run_pipeline(job_id: str, jobs_dir: Path) -> None:
    """Orchestrate the pipeline stages."""
    ctx = await _setup_pipeline(job_id, jobs_dir)
    try:
        analysis_results = await _run_paper_analysis(ctx)
        dedup_result = await _run_theme_dedup(ctx, analysis_results)
        review_results = await _run_theme_review(ctx, dedup_result, analysis_results)
        quarantined = await _run_aggregation(ctx, review_results, analysis_results)
        if not quarantined:
            await _finalize_pipeline(ctx)
    except Exception as exc:
        await _handle_pipeline_failure(ctx, exc)
    finally:
        _cleanup(ctx)


# ---------------------------------------------------------------------------
# Setup / teardown helpers
# ---------------------------------------------------------------------------


async def _setup_pipeline(job_id: str, jobs_dir: Path) -> PipelineContext:
    """Load papers, initialize emitter/tracker/indexer, mark job as running."""
    emitter = get_or_create_emitter(job_id, jobs_dir)
    job_path = jobs_dir / job_id

    # Load papers
    papers_data = await read_yaml(job_path / "papers.yaml")
    if not papers_data:
        raise ValueError("No papers found in papers.yaml")
    papers = [PaperEntry.model_validate(p) for p in papers_data]

    # Load paper markdown content — chunked papers have {paper_id}__chunk{NNN}.md
    # files instead of a single {paper_id}.md; fall back to the single file.
    paper_contents: dict[str, list[str]] = {}
    for paper in papers:
        chunk_paths = sorted(job_path.glob(f"{paper.paper_id}__chunk*.md"))
        if chunk_paths:
            paper_contents[paper.paper_id] = [
                await asyncio.to_thread(p.read_text) for p in chunk_paths
            ]
            continue
        md_path = job_path / f"{paper.paper_id}.md"
        if md_path.exists():
            paper_contents[paper.paper_id] = [await asyncio.to_thread(md_path.read_text)]

    tracker = ProgressTracker(job_id, jobs_dir, emitter, len(papers))

    # Initialize Qdrant (graceful — None if unavailable)
    indexer = get_indexer()
    if indexer:
        try:
            await indexer.ensure_collections()
            logger.info("Qdrant initialized — indexing enabled")
        except Exception:
            logger.warning("Qdrant available but collection init failed — indexing disabled")
            indexer = None
    else:
        logger.info("Qdrant not available — indexing disabled, YAML is source of truth")

    ctx = PipelineContext(
        job_id=job_id,
        job_path=job_path,
        jobs_dir=jobs_dir,
        papers=papers,
        paper_contents=paper_contents,
        emitter=emitter,
        tracker=tracker,
        indexer=indexer,
    )

    # Mark job as running
    now = datetime.now(UTC)
    status = JobStatus(
        job_id=job_id,
        status=JobState.RUNNING,
        stage=Stage.PAPER_ANALYSIS,
        progress=0.0,
        paper_count=len(papers),
        created_at=now,
        updated_at=now,
    )
    await write_status(job_id, status, jobs_dir)
    await emitter.emit(EventType.JOB_STARTED, {"paper_count": len(papers)})

    return ctx


async def _finalize_pipeline(ctx: PipelineContext) -> None:
    """Wait for Qdrant writes and mark job as completed."""
    if ctx.qdrant_tasks:
        await asyncio.gather(*ctx.qdrant_tasks, return_exceptions=True)

    now = datetime.now(UTC)
    final_status = JobStatus(
        job_id=ctx.job_id,
        status=JobState.COMPLETED,
        stage=Stage.AGGREGATION,
        progress=1.0,
        paper_count=len(ctx.papers),
        created_at=ctx.tracker.created_at,
        updated_at=now,
    )
    await write_status(ctx.job_id, final_status, ctx.jobs_dir)
    await ctx.emitter.emit(EventType.JOB_COMPLETED, {"progress": 1.0})


async def _handle_pipeline_failure(ctx: PipelineContext, exc: Exception) -> None:
    """Drain Qdrant writes, set FAILED status, emit failure event."""
    if ctx.qdrant_tasks:
        await asyncio.gather(*ctx.qdrant_tasks, return_exceptions=True)

    logger.error("Pipeline failed for job %s: %s", ctx.job_id, exc, exc_info=True)
    now = datetime.now(UTC)
    # Preserve original created_at from existing status
    existing_status = (
        await read_yaml(ctx.job_path / "status.yaml") if ctx.job_path.exists() else None
    )
    original_created = (
        existing_status.get("created_at", now) if existing_status else now
    )
    error_msg = "Pipeline failed. Check server logs for details."
    error_status = JobStatus(
        job_id=ctx.job_id,
        status=JobState.FAILED,
        stage="",
        progress=0.0,
        paper_count=0,
        created_at=original_created,
        updated_at=now,
        error=error_msg,
    )
    await write_status(ctx.job_id, error_status, ctx.jobs_dir)
    await ctx.emitter.emit(EventType.JOB_FAILED, {"error": error_msg})


def _cleanup(ctx: PipelineContext) -> None:
    """Clean up per-job registries to prevent memory leaks."""
    remove_emitter(ctx.job_id)
    # E8: Clean up per-job persistence lock
    release_lock(ctx.job_id)


# ---------------------------------------------------------------------------
# Stage functions
# ---------------------------------------------------------------------------


async def _run_paper_analysis(ctx: PipelineContext) -> AnalysisResults:
    """Stage 1: Paper Analysis — extract themes + claims per paper (parallel)."""
    analyzer = PaperAnalyzerAgent()
    await ctx.tracker.stage_start(Stage.PAPER_ANALYSIS, len(ctx.papers))
    analysis_results = await _run_parallel_per_paper(
        ctx.papers, ctx.paper_contents, analyzer, ctx.tracker, Stage.PAPER_ANALYSIS,
        ctx.job_path, emitter=ctx.emitter, merge_fn=merge_chunk_results,
    )
    # Persist per-paper themes and claims (split from unified result)
    for paper, result in analysis_results:
        themes_data = {"themes": result.get("themes", [])}
        claims_data = {"claims": result.get("claims", [])}
        await write_yaml(
            ctx.job_path / "themes" / f"{paper.paper_id}.yaml",
            themes_data,
            job_id=ctx.job_id,
        )
        await write_yaml(
            ctx.job_path / "claims" / f"{paper.paper_id}.yaml",
            claims_data,
            job_id=ctx.job_id,
        )
        if ctx.indexer:
            op = f"index_themes({paper.paper_id})"
            ctx.fire_qdrant(
                ctx.indexer.index_themes(ctx.job_id, paper.paper_id, themes_data),
                operation=op,
            )
            op = f"index_claims({paper.paper_id})"
            ctx.fire_qdrant(
                ctx.indexer.index_claims(ctx.job_id, paper.paper_id, claims_data),
                operation=op,
            )
        await ctx.emitter.emit(
            EventType.PAPER_ANALYZED,
            {
                "paper_id": paper.paper_id,
                "theme_count": len(result.get("themes", [])),
                "claim_count": len(result.get("claims", [])),
            },
        )
    await ctx.tracker.stage_complete(Stage.PAPER_ANALYSIS)
    return analysis_results


async def _run_theme_dedup(
    ctx: PipelineContext, analysis_results: AnalysisResults,
) -> DedupResult:
    """Stage 2: Theme Dedup — D&C: cluster, dedup per bucket (parallel), reconcile."""
    all_themes: list[dict[str, Any]] = []
    for _paper, result in analysis_results:
        all_themes.extend(result.get("themes", []))

    buckets = await cluster_themes(all_themes)
    theme_dedup = ThemeDedupAgent()
    await ctx.tracker.stage_start(Stage.THEME_DEDUP, len(buckets))

    async def _process_bucket(bucket_idx: int, indices: list[int]) -> dict[str, Any]:
        bucket_themes = [all_themes[i] for i in indices]
        dedup_cb = create_agent_event_callback(
            ctx.emitter, "ThemeDedup", Stage.THEME_DEDUP,
            context={
                "bucket": f"{bucket_idx}/{len(buckets)}",
                "theme_count": len(bucket_themes),
            },
        )
        result = await theme_dedup.run({"themes": bucket_themes}, on_event=dedup_cb)
        await ctx.tracker.stage_item_done(Stage.THEME_DEDUP, f"bucket-{bucket_idx}")
        return result

    bucket_results = await asyncio.gather(
        *[_process_bucket(idx, indices) for idx, indices in enumerate(buckets, 1)]
    )

    all_canonical: list[dict[str, Any]] = []
    merged_map: dict[str, list[str]] = {}
    for result in bucket_results:
        all_canonical.extend(result.get("themes", []))
        merged_map.update(result.get("theme_map", {}))

    final_themes, final_map = await reconcile_canonical_themes(all_canonical, merged_map)
    dedup_result: DedupResult = {"theme_map": final_map, "themes": final_themes}

    await write_yaml(ctx.job_path / "theme_map.yaml", dedup_result, job_id=ctx.job_id)
    if ctx.indexer:
        ctx.fire_qdrant(
            ctx.indexer.index_theme_map(ctx.job_id, dedup_result),
            operation="index_theme_map",
        )
    await ctx.emitter.emit(
        EventType.THEME_DEDUPLICATED,
        {"theme_count": len(dedup_result.get("themes", []))},
    )
    await ctx.tracker.stage_complete(Stage.THEME_DEDUP)
    return dedup_result


async def _run_theme_review(
    ctx: PipelineContext,
    dedup_result: DedupResult,
    analysis_results: AnalysisResults,
) -> ReviewResults:
    """Stage 3: Theme Review — synthesize claims per theme (batched, 5 per LLM call)."""
    canonical_themes = dedup_result.get("themes", [])
    all_claims: list[dict[str, Any]] = []
    for _paper, result in analysis_results:
        all_claims.extend(result.get("claims", []))

    theme_reviewer = ThemeReviewerAgent()
    await ctx.tracker.stage_start(Stage.THEME_REVIEW, len(canonical_themes))
    review_cb = create_agent_event_callback(
        ctx.emitter, "ThemeReviewer", Stage.THEME_REVIEW,
        context={"theme_count": len(canonical_themes)},
    )
    review_results = await theme_reviewer.run_batch(
        canonical_themes, all_claims, on_event=review_cb,
    )
    # Persist per-theme reviews
    for review_out in review_results:
        theme_id = review_out.get("theme_id", "")
        if theme_id:
            await write_yaml(
                ctx.job_path / "theme_reviews" / f"{theme_id}.yaml",
                review_out,
                job_id=ctx.job_id,
            )
            if ctx.indexer:
                op = f"index_theme_review({theme_id})"
                ctx.fire_qdrant(
                    ctx.indexer.index_theme_review(ctx.job_id, review_out),
                    operation=op,
                )
            await ctx.tracker.stage_item_done(Stage.THEME_REVIEW, theme_id)
    await ctx.tracker.stage_complete(Stage.THEME_REVIEW)
    return review_results


async def _run_aggregation(
    ctx: PipelineContext,
    review_results: ReviewResults,
    analysis_results: AnalysisResults,
) -> bool:
    """Stage 4: Aggregation — produce cohesive literature review with citations.

    Returns True if the job was quarantined by the post-aggregation judge
    gate (§8.2), False if it completed normally.
    """
    all_claims: list[dict[str, Any]] = []
    for _paper, result in analysis_results:
        all_claims.extend(result.get("claims", []))

    aggregator = AggregatorAgent()
    await ctx.tracker.stage_start(Stage.AGGREGATION, 1)
    agg_cb = create_agent_event_callback(
        ctx.emitter, "Aggregator", Stage.AGGREGATION,
        context={"theme_count": len(review_results)},
    )
    review = await aggregator.run({
        "theme_reviews": review_results,
        "claims": all_claims,
        "papers": [
            {"paper_id": p.paper_id, "title": p.title, "authors": p.authors}
            for p in ctx.papers
        ],
    }, on_event=agg_cb)

    # review.yaml is written regardless of the gate verdict — quarantine
    # flags content for manual review, it doesn't hide it (§7.4/§8.2 policy).
    await write_yaml(ctx.job_path / "review.yaml", review, job_id=ctx.job_id)
    if ctx.indexer:
        ctx.fire_qdrant(
            ctx.indexer.index_review(ctx.job_id, review), operation="index_review",
        )

    # Toxic gate (§7.4) runs before the judge gate (§8.2) — cheaper, narrower
    # check first; a job already being quarantined for toxic content doesn't
    # need the more expensive judge-model call too.
    toxic_result = await check_toxicity(review)
    if toxic_result.verdict == "quarantine":
        logger.warning(
            "Job %s quarantined by toxic gate: %s", ctx.job_id, toxic_result.reason,
        )
        await quarantine_job(
            ctx.job_id, ctx.jobs_dir, ctx.emitter,
            created_at=ctx.tracker.created_at,
            paper_count=len(ctx.papers),
            stage=Stage.AGGREGATION,
            reason=toxic_result.reason or "toxic gate failed",
        )
        return True

    gate_result = await score_review(review, all_claims)
    if gate_result.verdict == "quarantine":
        logger.warning(
            "Job %s quarantined by judge gate: %s", ctx.job_id, gate_result.reason,
        )
        await quarantine_job(
            ctx.job_id, ctx.jobs_dir, ctx.emitter,
            created_at=ctx.tracker.created_at,
            paper_count=len(ctx.papers),
            stage=Stage.AGGREGATION,
            reason=gate_result.reason or "judge gate failed",
        )
        return True

    await ctx.emitter.emit(EventType.REVIEW_GENERATED, {"title": review.get("title", "")})
    await ctx.tracker.stage_complete(Stage.AGGREGATION)
    return False


# ---------------------------------------------------------------------------
# Parallel execution helper
# ---------------------------------------------------------------------------


async def _safe_qdrant(coro: Coroutine, *, operation: str = "unknown") -> None:
    """Run a Qdrant write coroutine, swallowing any errors."""
    try:
        await coro
    except Exception:
        logger.debug("Qdrant %s failed (non-blocking)", operation, exc_info=True)


async def _run_parallel_per_paper(
    papers: list[PaperEntry],
    paper_contents: dict[str, list[str]],
    agent: Agent,
    tracker: ProgressTracker,
    stage: str,
    job_path: Path,
    extra_inputs: dict[str, dict[str, Any]] | None = None,
    emitter: EventEmitter | None = None,
    merge_fn: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None,
) -> list[tuple[PaperEntry, dict[str, Any]]]:
    """Run an agent in parallel across all papers.

    Args:
        extra_inputs: Optional mapping of {key: {paper_id: value}} to merge
            into each agent call. For example, {"themes": {pid: [...]}} adds
            input["themes"] per paper.
        emitter: Optional EventEmitter for agent-level event forwarding.
        merge_fn: Required when a paper has more than one content chunk —
            reconciles the per-chunk results into one paper-level result.
            A chunk whose call fails is logged and dropped; the paper only
            fails if every one of its chunks fails.
    """
    inner = getattr(agent, "_agent", None)
    agent_name = (
        getattr(inner, "name", agent.__class__.__name__)
        if inner
        else agent.__class__.__name__
    )

    async def call_agent(paper: PaperEntry, content: str) -> dict[str, Any]:
        input_dict: dict[str, Any] = {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "content": content,
            "authors": paper.authors,
            "page_count": paper.page_count,
        }
        if extra_inputs:
            for key, mapping in extra_inputs.items():
                input_dict[key] = mapping.get(paper.paper_id, [])
        kwargs: dict[str, Any] = {}
        if emitter is not None:
            kwargs["on_event"] = create_agent_event_callback(
                emitter, agent_name, stage, paper_id=paper.paper_id,
                context={"paper_title": paper.title},
            )
        return await agent.run(input_dict, **kwargs)

    async def process_one(paper: PaperEntry) -> dict[str, Any] | Exception:
        contents = paper_contents.get(paper.paper_id) or [""]
        try:
            if len(contents) == 1:
                result = await call_agent(paper, contents[0])
            else:
                chunk_results = await asyncio.gather(
                    *[call_agent(paper, c) for c in contents], return_exceptions=True,
                )
                successful = [r for r in chunk_results if not isinstance(r, Exception)]
                if not successful:
                    raise chunk_results[0]  # all chunks failed
                failed = len(chunk_results) - len(successful)
                if failed:
                    logger.warning(
                        "%d/%d chunks failed for paper %s in %s — merging %d successful",
                        failed, len(chunk_results), paper.paper_id, stage, len(successful),
                    )
                if merge_fn is None:
                    raise RuntimeError(
                        f"paper {paper.paper_id} has {len(contents)} chunks but no "
                        f"merge_fn was provided to _run_parallel_per_paper"
                    )
                result = merge_fn(successful)
            await tracker.stage_item_done(stage, paper.paper_id)
            return result
        except TopicGateRejectedError as exc:
            logger.info(
                "Paper %s rejected by topic gate: %s", paper.paper_id, exc.reason,
            )
            await tracker.stage_item_done(stage, paper.paper_id)
            if emitter is not None:
                await emitter.emit(
                    EventType.PAPER_REJECTED,
                    {"paper_id": paper.paper_id, "reason": exc.reason},
                )
            return exc
        except Exception as exc:
            logger.error("Paper %s failed in %s: %s", paper.paper_id, stage, exc)
            await tracker.stage_item_done(stage, paper.paper_id)
            return exc

    raw_results = await asyncio.gather(*[process_one(p) for p in papers])

    # Collect results paired with their paper, re-raising if ALL papers failed
    successful: list[tuple[PaperEntry, dict[str, Any]]] = []
    errors: list[Exception] = []
    for paper, r in zip(papers, raw_results):
        if isinstance(r, Exception):
            errors.append(r)
        else:
            successful.append((paper, r))

    if not successful:
        raise RuntimeError(
            f"All {len(papers)} papers failed in {stage}: {errors[0]}"
        )
    if errors:
        logger.warning(
            "%d/%d papers failed in %s — continuing with %d successful",
            len(errors), len(papers), stage, len(successful),
        )

    return successful
