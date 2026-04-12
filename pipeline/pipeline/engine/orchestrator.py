"""Pipeline orchestrator: runs stages in order with parallel execution and sync barriers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeline.agents import (
    AggregatorAgent,
    PaperAnalyzerAgent,
    ThemeDedupAgent,
    ThemeReviewerAgent,
)
from pipeline.agents.event_bridge import create_agent_event_callback
from pipeline.core import (
    EventType,
    JobState,
    JobStatus,
    PaperEntry,
    read_yaml,
    write_status,
    write_yaml,
)
from pipeline.core.qdrant import get_indexer
from pipeline.ws.stream import get_or_create_emitter, remove_emitter

from .progress import ProgressTracker
from .stages import Stage

logger = logging.getLogger(__name__)


async def _safe_qdrant(coro: Coroutine, *, operation: str = "unknown") -> None:
    """Run a Qdrant write coroutine, swallowing any errors."""
    try:
        await coro
    except Exception:
        logger.debug("Qdrant %s failed (non-blocking)", operation, exc_info=True)


async def run_pipeline(job_id: str, jobs_dir: Path) -> None:
    """Run the full pipeline for a job. Intended to be launched via asyncio.create_task."""
    emitter = get_or_create_emitter(job_id, jobs_dir)
    job_path = jobs_dir / job_id
    qdrant_tasks: set[asyncio.Task] = set()

    def _fire_qdrant(coro: Coroutine, *, operation: str = "write") -> None:
        """Schedule a Qdrant write as fire-and-forget background task."""
        task = asyncio.create_task(_safe_qdrant(coro, operation=operation))
        qdrant_tasks.add(task)
        task.add_done_callback(qdrant_tasks.discard)

    try:
        # Load papers
        papers_data = await read_yaml(job_path / "papers.yaml")
        if not papers_data:
            raise ValueError("No papers found in papers.yaml")
        papers = [PaperEntry.model_validate(p) for p in papers_data]

        # Load paper markdown content
        paper_contents: dict[str, str] = {}
        for paper in papers:
            md_path = job_path / f"{paper.paper_id}.md"
            if md_path.exists():
                paper_contents[paper.paper_id] = await asyncio.to_thread(md_path.read_text)

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

        # --- Stage 1: Paper Analysis (themes + claims in one pass, per-paper, parallel) ---
        analyzer = PaperAnalyzerAgent()
        await tracker.stage_start(Stage.PAPER_ANALYSIS, len(papers))
        analysis_results = await _run_parallel_per_paper(
            papers, paper_contents, analyzer, tracker, Stage.PAPER_ANALYSIS, job_path,
            emitter=emitter,
        )
        # Persist per-paper themes and claims (split from unified result)
        for paper, result in zip(papers, analysis_results):
            themes_data = {"themes": result.get("themes", [])}
            claims_data = {"claims": result.get("claims", [])}
            await write_yaml(
                job_path / "themes" / f"{paper.paper_id}.yaml",
                themes_data,
                job_id=job_id,
            )
            await write_yaml(
                job_path / "claims" / f"{paper.paper_id}.yaml",
                claims_data,
                job_id=job_id,
            )
            if indexer:
                op = f"index_themes({paper.paper_id})"
                _fire_qdrant(indexer.index_themes(job_id, paper.paper_id, themes_data), operation=op)
                op = f"index_claims({paper.paper_id})"
                _fire_qdrant(indexer.index_claims(job_id, paper.paper_id, claims_data), operation=op)
            await emitter.emit(
                EventType.PAPER_ANALYZED,
                {
                    "paper_id": paper.paper_id,
                    "theme_count": len(result.get("themes", [])),
                    "claim_count": len(result.get("claims", [])),
                },
            )
        await tracker.stage_complete(Stage.PAPER_ANALYSIS)

        # === SYNC BARRIER: all per-paper analysis complete ===

        # --- Stage 2: Theme Dedup (single pass) ---
        all_themes = []
        for result in analysis_results:
            all_themes.extend(result.get("themes", []))

        theme_dedup = ThemeDedupAgent()
        await tracker.stage_start(Stage.THEME_DEDUP, 1)
        dedup_cb = create_agent_event_callback(
            emitter, "ThemeDedup", Stage.THEME_DEDUP,
            context={"theme_count": len(all_themes)},
        )
        dedup_result = await theme_dedup.run({"themes": all_themes, "job_dir": str(job_path), "_emitter": emitter}, on_event=dedup_cb)
        await write_yaml(job_path / "theme_map.yaml", dedup_result, job_id=job_id)
        if indexer:
            _fire_qdrant(indexer.index_theme_map(job_id, dedup_result), operation="index_theme_map")
        await emitter.emit(
            EventType.THEME_DEDUPLICATED,
            {"theme_count": len(dedup_result.get("themes", []))},
        )
        await tracker.stage_complete(Stage.THEME_DEDUP)

        # === SYNC BARRIER: dedup complete ===

        # --- Stage 3: Theme Review (batched — 5 themes per LLM call) ---
        canonical_themes = dedup_result.get("themes", [])
        all_claims = []
        for result in analysis_results:
            all_claims.extend(result.get("claims", []))

        theme_reviewer = ThemeReviewerAgent()
        await tracker.stage_start(Stage.THEME_REVIEW, len(canonical_themes))
        review_cb = create_agent_event_callback(
            emitter, "ThemeReviewer", Stage.THEME_REVIEW,
            context={"theme_count": len(canonical_themes)},
        )
        review_results = await theme_reviewer.run_batch(
            canonical_themes, all_claims, on_event=review_cb,
            job_dir=str(job_path), emitter=emitter,
        )
        # Persist per-theme reviews
        for review_out in review_results:
            theme_id = review_out.get("theme_id", "")
            if theme_id:
                await write_yaml(
                    job_path / "theme_reviews" / f"{theme_id}.yaml",
                    review_out,
                    job_id=job_id,
                )
                if indexer:
                    op = f"index_theme_review({theme_id})"
                    _fire_qdrant(indexer.index_theme_review(job_id, review_out), operation=op)
                await tracker.stage_item_done(Stage.THEME_REVIEW, theme_id)
        await tracker.stage_complete(Stage.THEME_REVIEW)

        # === SYNC BARRIER: all theme reviews complete ===

        # --- Stage 4: Aggregation (single pass) ---
        aggregator = AggregatorAgent()
        await tracker.stage_start(Stage.AGGREGATION, 1)
        agg_cb = create_agent_event_callback(
            emitter, "Aggregator", Stage.AGGREGATION,
            context={"theme_count": len(review_results)},
        )
        review = await aggregator.run({
            "theme_reviews": review_results,
            "claims": all_claims,
            "papers": [
                {"paper_id": p.paper_id, "title": p.title, "authors": p.authors}
                for p in papers
            ],
            "job_dir": str(job_path),
            "_emitter": emitter,
        }, on_event=agg_cb)
        await write_yaml(job_path / "review.yaml", review, job_id=job_id)
        if indexer:
            _fire_qdrant(indexer.index_review(job_id, review), operation="index_review")
        await emitter.emit(EventType.REVIEW_GENERATED, {"title": review.get("title", "")})
        await tracker.stage_complete(Stage.AGGREGATION)

        # Wait for all pending Qdrant writes before marking complete
        if qdrant_tasks:
            await asyncio.gather(*qdrant_tasks, return_exceptions=True)

        # Mark job as completed
        now = datetime.now(UTC)
        final_status = JobStatus(
            job_id=job_id,
            status=JobState.COMPLETED,
            stage=Stage.AGGREGATION,
            progress=1.0,
            paper_count=len(papers),
            created_at=now,
            updated_at=now,
        )
        await write_status(job_id, final_status, jobs_dir)
        await emitter.emit(EventType.JOB_COMPLETED, {"progress": 1.0})

    except Exception as exc:
        # Drain any pending Qdrant writes on failure too
        if qdrant_tasks:
            await asyncio.gather(*qdrant_tasks, return_exceptions=True)

        logger.error("Pipeline failed for job %s: %s", job_id, exc, exc_info=True)
        now = datetime.now(UTC)
        error_status = JobStatus(
            job_id=job_id,
            status=JobState.FAILED,
            stage="",
            progress=0.0,
            paper_count=0,
            created_at=now,
            updated_at=now,
            error="An internal error occurred. Check server logs for details.",
        )
        await write_status(job_id, error_status, jobs_dir)
        await emitter.emit(EventType.JOB_FAILED, {"error": "An internal error occurred."})

    finally:
        # Clean up per-job registries to prevent memory leaks
        remove_emitter(job_id)


async def _run_parallel_per_paper(
    papers: list[PaperEntry],
    paper_contents: dict[str, str],
    agent: Any,
    tracker: ProgressTracker,
    stage: str,
    job_path: Path,
    extra_inputs: dict[str, dict[str, Any]] | None = None,
    emitter: Any | None = None,
) -> list[dict[str, Any]]:
    """Run an agent in parallel across all papers.

    Args:
        extra_inputs: Optional mapping of {key: {paper_id: value}} to merge
            into each agent call. For example, {"themes": {pid: [...]}} adds
            input["themes"] per paper.
        emitter: Optional EventEmitter for agent-level event forwarding.
    """
    agent_name = getattr(agent, "_agent", None)
    agent_name = getattr(agent_name, "name", agent.__class__.__name__) if agent_name else agent.__class__.__name__

    async def process_one(paper: PaperEntry) -> dict[str, Any] | Exception:
        content = paper_contents.get(paper.paper_id, "")
        input_dict: dict[str, Any] = {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "content": content,
            "job_dir": str(job_path),
            "_emitter": emitter,
        }
        if extra_inputs:
            for key, mapping in extra_inputs.items():
                input_dict[key] = mapping.get(paper.paper_id, [])
        try:
            kwargs: dict[str, Any] = {}
            if emitter is not None:
                kwargs["on_event"] = create_agent_event_callback(
                    emitter, agent_name, stage, paper_id=paper.paper_id,
                    context={"paper_title": paper.title},
                )
            result = await agent.run(input_dict, **kwargs)
            await tracker.stage_item_done(stage, paper.paper_id)
            return result
        except Exception as exc:
            logger.error("Paper %s failed in %s: %s", paper.paper_id, stage, exc)
            await tracker.stage_item_done(stage, paper.paper_id)
            return exc

    raw_results = await asyncio.gather(*[process_one(p) for p in papers])

    # Collect results, re-raising if ALL papers failed
    results: list[dict[str, Any]] = []
    errors: list[Exception] = []
    for r in raw_results:
        if isinstance(r, Exception):
            errors.append(r)
        else:
            results.append(r)

    if not results:
        raise RuntimeError(
            f"All {len(papers)} papers failed in {stage}: {errors[0]}"
        )
    if errors:
        logger.warning(
            "%d/%d papers failed in %s — continuing with %d successful",
            len(errors), len(papers), stage, len(results),
        )

    return results
