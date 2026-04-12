"""Durable pipeline workflow using Restate."""

from __future__ import annotations

import logging
from pathlib import Path

from restate import Workflow, WorkflowContext

from pipeline.engine.orchestrator import (
    _cleanup,
    _finalize_pipeline,
    _handle_pipeline_failure,
    _run_aggregation,
    _run_paper_analysis,
    _run_theme_dedup,
    _run_theme_review,
    _setup_pipeline,
)

logger = logging.getLogger(__name__)

pipeline_workflow = Workflow("PipelineWorkflow")


@pipeline_workflow.main()
async def run(ctx: WorkflowContext, request: dict) -> dict:
    """Execute the literature review pipeline with durable steps.

    Each stage is journaled by Restate. On crash/restart, completed
    stages are replayed from the journal (not re-executed).
    """
    job_id = ctx.key()
    jobs_dir = Path(request["jobs_dir"])

    ctx_pipeline = await _setup_pipeline(job_id, jobs_dir)

    try:
        analysis = await ctx.run(
            "paper_analysis", lambda: _run_paper_analysis(ctx_pipeline)
        )
        dedup = await ctx.run(
            "theme_dedup", lambda: _run_theme_dedup(ctx_pipeline, analysis)
        )
        reviews = await ctx.run(
            "theme_review",
            lambda: _run_theme_review(ctx_pipeline, dedup, analysis),
        )
        await ctx.run(
            "aggregation",
            lambda: _run_aggregation(ctx_pipeline, reviews, analysis),
        )
        await _finalize_pipeline(ctx_pipeline)
        return {"status": "completed", "job_id": job_id}
    except Exception as exc:
        await _handle_pipeline_failure(ctx_pipeline, exc)
        return {"status": "failed", "job_id": job_id}
    finally:
        _cleanup(ctx_pipeline)
