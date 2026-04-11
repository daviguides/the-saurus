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
    ClaimExtractorAgent,
    ThemeDedupAgent,
    ThemeExtractorAgent,
    ThemeReviewerAgent,
)
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
from pipeline.ws.stream import get_or_create_emitter

from .progress import ProgressTracker
from .stages import Stage

logger = logging.getLogger(__name__)


async def _safe_qdrant(coro: Coroutine) -> None:
    """Run a Qdrant write coroutine, swallowing any errors."""
    try:
        await coro
    except Exception:
        logger.warning("Qdrant write failed (non-blocking)", exc_info=True)


async def run_pipeline(job_id: str, jobs_dir: Path) -> None:
    """Run the full pipeline for a job. Intended to be launched via asyncio.create_task."""
    emitter = get_or_create_emitter(job_id, jobs_dir)
    job_path = jobs_dir / job_id
    qdrant_tasks: set[asyncio.Task] = set()

    def _fire_qdrant(coro: Coroutine) -> None:
        """Schedule a Qdrant write as fire-and-forget background task."""
        task = asyncio.create_task(_safe_qdrant(coro))
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
                paper_contents[paper.paper_id] = md_path.read_text()

        tracker = ProgressTracker(job_id, jobs_dir, emitter, len(papers))

        # Initialize Qdrant collections (fire-and-forget)
        try:
            indexer = get_indexer()
            await indexer.ensure_collections()
        except Exception:
            logger.warning("Qdrant init failed — writes will be skipped", exc_info=True)
            indexer = None

        # Mark job as running
        now = datetime.now(UTC)
        status = JobStatus(
            job_id=job_id,
            status=JobState.RUNNING,
            stage=Stage.THEME_EXTRACTION,
            progress=0.0,
            paper_count=len(papers),
            created_at=now,
            updated_at=now,
        )
        await write_status(job_id, status, jobs_dir)
        await emitter.emit(EventType.JOB_STARTED, {"paper_count": len(papers)})

        # --- Stage 1: Theme Extraction (per-paper, parallel) ---
        theme_extractor = ThemeExtractorAgent()
        await tracker.stage_start(Stage.THEME_EXTRACTION, len(papers))
        theme_results = await _run_parallel_per_paper(
            papers, paper_contents, theme_extractor, tracker, Stage.THEME_EXTRACTION, job_path
        )
        # Persist per-paper themes
        for paper, result in zip(papers, theme_results):
            await write_yaml(
                job_path / "themes" / f"{paper.paper_id}.yaml",
                result,
                job_id=job_id,
            )
            if indexer:
                _fire_qdrant(indexer.index_themes(job_id, paper.paper_id, result))
            await emitter.emit(
                EventType.THEME_EXTRACTED,
                {"paper_id": paper.paper_id, "theme_count": len(result.get("themes", []))},
            )
        await tracker.stage_complete(Stage.THEME_EXTRACTION)

        # --- Stage 2: Claim Extraction (per-paper, parallel) ---
        claim_extractor = ClaimExtractorAgent()
        themes_by_paper = {
            paper.paper_id: result.get("themes", []) for paper, result in zip(papers, theme_results)
        }
        await tracker.stage_start(Stage.CLAIM_EXTRACTION, len(papers))
        claim_results = await _run_parallel_per_paper(
            papers,
            paper_contents,
            claim_extractor,
            tracker,
            Stage.CLAIM_EXTRACTION,
            job_path,
            extra_inputs={"themes": themes_by_paper},
        )
        # Persist per-paper claims
        for paper, result in zip(papers, claim_results):
            await write_yaml(
                job_path / "claims" / f"{paper.paper_id}.yaml",
                result,
                job_id=job_id,
            )
            if indexer:
                _fire_qdrant(indexer.index_claims(job_id, paper.paper_id, result))
            await emitter.emit(
                EventType.CLAIM_EXTRACTED,
                {"paper_id": paper.paper_id, "claim_count": len(result.get("claims", []))},
            )
        await tracker.stage_complete(Stage.CLAIM_EXTRACTION)

        # === SYNC BARRIER: all per-paper stages complete ===

        # --- Stage 3: Theme Dedup (single pass) ---
        all_themes = []
        for result in theme_results:
            all_themes.extend(result.get("themes", []))

        theme_dedup = ThemeDedupAgent()
        await tracker.stage_start(Stage.THEME_DEDUP, 1)
        dedup_result = await theme_dedup.run({"themes": all_themes})
        await write_yaml(job_path / "theme_map.yaml", dedup_result, job_id=job_id)
        if indexer:
            _fire_qdrant(indexer.index_theme_map(job_id, dedup_result))
        await emitter.emit(
            EventType.THEME_DEDUPLICATED,
            {"theme_count": len(dedup_result.get("themes", []))},
        )
        await tracker.stage_complete(Stage.THEME_DEDUP)

        # === SYNC BARRIER: dedup complete ===

        # --- Stage 4: Theme Review (per-theme, parallel) ---
        canonical_themes = dedup_result.get("themes", [])
        all_claims = []
        for result in claim_results:
            all_claims.extend(result.get("claims", []))

        theme_reviewer = ThemeReviewerAgent()
        await tracker.stage_start(Stage.THEME_REVIEW, len(canonical_themes))
        review_results = await _run_parallel_per_theme(
            canonical_themes,
            all_claims,
            theme_reviewer,
            tracker,
            Stage.THEME_REVIEW,
            job_path,
            job_id,
            indexer,
            _fire_qdrant,
        )
        await tracker.stage_complete(Stage.THEME_REVIEW)

        # === SYNC BARRIER: all theme reviews complete ===

        # --- Stage 5: Aggregation (single pass) ---
        aggregator = AggregatorAgent()
        await tracker.stage_start(Stage.AGGREGATION, 1)
        review = await aggregator.run({
            "theme_reviews": review_results,
            "claims": all_claims,
            "papers": [
                {"paper_id": p.paper_id, "title": p.title, "authors": p.authors}
                for p in papers
            ],
        })
        await write_yaml(job_path / "review.yaml", review, job_id=job_id)
        if indexer:
            _fire_qdrant(indexer.index_review(job_id, review))
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

        now = datetime.now(UTC)
        error_status = JobStatus(
            job_id=job_id,
            status=JobState.FAILED,
            stage="",
            progress=0.0,
            paper_count=0,
            created_at=now,
            updated_at=now,
            error=str(exc),
        )
        await write_status(job_id, error_status, jobs_dir)
        await emitter.emit(EventType.JOB_FAILED, {"error": str(exc)})


async def _run_parallel_per_paper(
    papers: list[PaperEntry],
    paper_contents: dict[str, str],
    agent: Any,
    tracker: ProgressTracker,
    stage: str,
    job_path: Path,
    extra_inputs: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Run an agent in parallel across all papers.

    Args:
        extra_inputs: Optional mapping of {key: {paper_id: value}} to merge
            into each agent call. For example, {"themes": {pid: [...]}} adds
            input["themes"] per paper.
    """

    async def process_one(paper: PaperEntry) -> dict[str, Any] | Exception:
        content = paper_contents.get(paper.paper_id, "")
        input_dict: dict[str, Any] = {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "content": content,
        }
        if extra_inputs:
            for key, mapping in extra_inputs.items():
                input_dict[key] = mapping.get(paper.paper_id, [])
        try:
            result = await agent.run(input_dict)
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


async def _run_parallel_per_theme(
    themes: list[dict[str, Any]],
    all_claims: list[dict[str, Any]],
    agent: Any,
    tracker: ProgressTracker,
    stage: str,
    job_path: Path,
    job_id: str,
    indexer: Any | None = None,
    fire_qdrant: Any | None = None,
) -> list[dict[str, Any]]:
    """Run theme reviewer in parallel across all themes."""

    # Build claim lookup by paper_id for rough association
    claims_by_paper: dict[str, list[dict[str, Any]]] = {}
    for claim in all_claims:
        pid = claim.get("source", {}).get("paper_id", "")
        claims_by_paper.setdefault(pid, []).append(claim)

    async def process_one(theme: dict[str, Any]) -> dict[str, Any] | Exception:
        paper_ids = theme.get("paper_ids", [theme.get("paper_id", "")])
        related_claims: list[dict[str, Any]] = []
        for pid in paper_ids:
            related_claims.extend(claims_by_paper.get(pid, []))
        try:
            result = await agent.run({"theme": theme, "claims": related_claims})
            theme_id = theme["id"]
            await write_yaml(
                job_path / "theme_reviews" / f"{theme_id}.yaml",
                result,
                job_id=job_id,
            )
            if indexer and fire_qdrant:
                fire_qdrant(indexer.index_theme_review(job_id, result))
            await tracker.stage_item_done(stage, theme_id)
            return result
        except Exception as exc:
            logger.error("Theme %s failed: %s", theme.get("id", "?"), exc)
            await tracker.stage_item_done(stage, theme.get("id", ""))
            return exc

    raw_results = await asyncio.gather(*[process_one(t) for t in themes])

    results: list[dict[str, Any]] = []
    errors: list[Exception] = []
    for r in raw_results:
        if isinstance(r, Exception):
            errors.append(r)
        else:
            results.append(r)

    if not results:
        raise RuntimeError(
            f"All {len(themes)} themes failed in {stage}: {errors[0]}"
        )
    if errors:
        logger.warning(
            "%d/%d themes failed in %s — continuing with %d successful",
            len(errors), len(themes), stage, len(results),
        )

    return results
