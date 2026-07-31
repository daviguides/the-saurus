"""Tests for pipeline engine orchestrator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from pipeline.agents import (
    Agent,
    StubAggregator,
    StubPaperAnalyzer,
    StubThemeDedup,
    StubThemeReviewer,
)
from pipeline.agents.judge_gate import JudgeGateResult
from pipeline.core import Event, EventEmitter, EventType, JobState, read_status, read_yaml
from pipeline.engine import Stage, run_pipeline
from pipeline.engine.stages import STAGES

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def jobs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "jobs"
    d.mkdir()
    return d


def _create_test_job(jobs_dir: Path, paper_count: int = 2) -> tuple[str, list[str]]:
    """Create a minimal job directory with papers.yaml and markdown files."""
    import yaml

    job_id = str(uuid4())
    job_path = jobs_dir / job_id
    job_path.mkdir()
    for subdir in ("themes", "claims", "theme_reviews"):
        (job_path / subdir).mkdir()

    (job_path / "events.ndjson").touch()

    now = datetime.now(UTC).isoformat()
    papers = []
    paper_ids = []
    for i in range(paper_count):
        pid = str(uuid4())
        paper_ids.append(pid)
        papers.append({
            "paper_id": pid,
            "filename": f"paper{i + 1}.pdf",
            "title": f"Test Paper {i + 1}",
            "authors": [f"Author {i + 1}"],
            "page_count": 3,
            "ingested_at": now,
        })
        # Write paper markdown
        (job_path / f"{pid}.md").write_text(
            f"# Test Paper {i + 1}\n\nThis is the content of test paper {i + 1}.\n"
        )

    with open(job_path / "papers.yaml", "w") as f:
        yaml.safe_dump(papers, f)

    # Write initial status
    status = {
        "job_id": job_id,
        "status": "pending",
        "stage": "",
        "progress": 0.0,
        "paper_count": paper_count,
        "created_at": now,
        "updated_at": now,
        "error": None,
    }
    with open(job_path / "status.yaml", "w") as f:
        yaml.safe_dump(status, f)

    return job_id, paper_ids


def _collect_events(emitter: EventEmitter) -> list[Event]:
    """Add a listener that collects all events."""
    events: list[Event] = []

    async def listener(event: Event) -> None:
        events.append(event)

    emitter.add_listener(listener)
    return events


# ---------------------------------------------------------------------------
# Stub Agent Tests
# ---------------------------------------------------------------------------


class TestStubAgents:
    async def test_stubs_satisfy_protocol(self):
        assert isinstance(StubPaperAnalyzer(), Agent)
        assert isinstance(StubThemeDedup(), Agent)
        assert isinstance(StubThemeReviewer(), Agent)
        assert isinstance(StubAggregator(), Agent)

    async def test_paper_analyzer_output(self):
        agent = StubPaperAnalyzer()
        result = await agent.run({"paper_id": "p1", "title": "My Paper", "content": "text"})
        assert "themes" in result
        assert "claims" in result
        assert len(result["themes"]) == 1
        assert len(result["claims"]) == 1
        theme = result["themes"][0]
        assert "id" in theme
        assert "name" in theme
        assert theme["paper_id"] == "p1"

    async def test_theme_dedup_output(self):
        agent = StubThemeDedup()
        themes = [
            {"id": "t1", "name": "Theme 1", "description": "desc1", "paper_id": "p1"},
            {"id": "t2", "name": "Theme 2", "description": "desc2", "paper_id": "p2"},
        ]
        result = await agent.run({"themes": themes})
        assert "theme_map" in result
        assert "themes" in result
        assert len(result["themes"]) == 2

    async def test_theme_reviewer_output(self):
        agent = StubThemeReviewer()
        theme = {"id": "t1", "name": "Theme 1"}
        claims = [{"id": "c1", "text": "claim"}, {"id": "c2", "text": "claim2"}]
        result = await agent.run({"theme": theme, "claims": claims})
        assert result["theme_id"] == "t1"
        assert "review" in result
        assert result["claim_ids"] == ["c1", "c2"]

    async def test_aggregator_output(self):
        agent = StubAggregator()
        reviews = [
            {"theme_id": "t1", "label": "Theme 1", "review": "text", "claim_ids": ["c1"]},
        ]
        result = await agent.run({"theme_reviews": reviews})
        assert result["title"] == "Literature Review"
        assert "sections" in result
        assert "references" in result


# ---------------------------------------------------------------------------
# Stage Ordering Tests
# ---------------------------------------------------------------------------


class TestStageDefinitions:
    def test_stages_ordered(self):
        assert STAGES == [
            Stage.PAPER_ANALYSIS,
            Stage.THEME_DEDUP,
            Stage.THEME_REVIEW,
            Stage.AGGREGATION,
        ]

    def test_stage_values(self):
        assert Stage.PAPER_ANALYSIS == "paper_analysis"
        assert Stage.AGGREGATION == "aggregation"


# ---------------------------------------------------------------------------
# Full Pipeline Tests
# ---------------------------------------------------------------------------


def _patch_qdrant():
    """Disable Qdrant indexing in tests."""
    return patch("pipeline.engine.orchestrator.get_indexer", return_value=None)


def _patch_paper_analyzer():
    return patch(
        "pipeline.engine.orchestrator.PaperAnalyzerAgent",
        return_value=StubPaperAnalyzer(),
    )


def _patch_theme_dedup():
    return patch(
        "pipeline.engine.orchestrator.ThemeDedupAgent",
        return_value=StubThemeDedup(),
    )


def _patch_theme_reviewer():
    return patch(
        "pipeline.engine.orchestrator.ThemeReviewerAgent",
        return_value=StubThemeReviewer(),
    )


def _patch_aggregator():
    return patch(
        "pipeline.engine.orchestrator.AggregatorAgent",
        return_value=StubAggregator(),
    )


class TestPipelineExecution:
    async def test_full_pipeline_completes(self, jobs_dir: Path):
        """Pipeline runs all stages and sets status to COMPLETED."""
        job_id, paper_ids = _create_test_job(jobs_dir, paper_count=2)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_qdrant(),
            _patch_paper_analyzer(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        # Check final status
        status = await read_status(job_id, jobs_dir)
        assert status is not None
        assert status.status == JobState.COMPLETED
        assert status.progress == 1.0

        # Check events include job lifecycle
        event_types = [e.event_type for e in events]
        assert EventType.JOB_STARTED in event_types
        assert EventType.JOB_COMPLETED in event_types

    async def test_stage_order_in_events(self, jobs_dir: Path):
        """Stages execute in correct order: paper_analysis -> dedup -> review -> aggregation."""
        job_id, _ = _create_test_job(jobs_dir, paper_count=2)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_qdrant(),
            _patch_paper_analyzer(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        # Extract stage_started events in order
        stage_starts = [
            e.payload["stage"]
            for e in events
            if e.event_type == EventType.STAGE_STARTED
        ]
        assert stage_starts == [
            Stage.PAPER_ANALYSIS,
            Stage.THEME_DEDUP,
            Stage.THEME_REVIEW,
            Stage.AGGREGATION,
        ]

    async def test_sync_barriers(self, jobs_dir: Path):
        """Theme dedup starts only after paper analysis completes."""
        job_id, _ = _create_test_job(jobs_dir, paper_count=3)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_qdrant(),
            _patch_paper_analyzer(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        # Find positions of key events
        analysis_complete_positions = [
            i
            for i, e in enumerate(events)
            if e.event_type == EventType.STAGE_COMPLETED
            and e.payload.get("stage") == Stage.PAPER_ANALYSIS
        ]
        dedup_start_positions = [
            i
            for i, e in enumerate(events)
            if e.event_type == EventType.STAGE_STARTED
            and e.payload.get("stage") == Stage.THEME_DEDUP
        ]

        assert len(analysis_complete_positions) >= 1
        assert len(dedup_start_positions) == 1
        # Dedup starts after paper analysis completes
        assert dedup_start_positions[0] > analysis_complete_positions[-1]

    async def test_persistence_artifacts(self, jobs_dir: Path):
        """Pipeline writes all expected intermediate files."""
        job_id, paper_ids = _create_test_job(jobs_dir, paper_count=2)
        emitter = EventEmitter(job_id, jobs_dir)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_qdrant(),
            _patch_paper_analyzer(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        job_path = jobs_dir / job_id

        # Per-paper theme and claim files
        for pid in paper_ids:
            assert (job_path / "themes" / f"{pid}.yaml").exists()
            assert (job_path / "claims" / f"{pid}.yaml").exists()

        # Theme map
        assert (job_path / "theme_map.yaml").exists()

        # Final review
        assert (job_path / "review.yaml").exists()
        review = await read_yaml(job_path / "review.yaml")
        assert review is not None
        assert review["title"] == "Literature Review"

    async def test_status_transitions(self, jobs_dir: Path):
        """Job status transitions from PENDING through RUNNING to COMPLETED."""
        job_id, _ = _create_test_job(jobs_dir, paper_count=1)
        emitter = EventEmitter(job_id, jobs_dir)
        statuses: list[str] = []

        original_emit = emitter.emit

        async def tracking_emit(event_type, payload=None):
            event = await original_emit(event_type, payload)
            s = await read_status(job_id, jobs_dir)
            if s:
                statuses.append(s.status)
            return event

        emitter.emit = tracking_emit

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_qdrant(),
            _patch_paper_analyzer(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        assert JobState.RUNNING in statuses
        assert statuses[-1] == JobState.COMPLETED

    async def test_failure_sets_failed_status(self, jobs_dir: Path):
        """If an agent raises, the job status is set to FAILED."""
        job_id, _ = _create_test_job(jobs_dir, paper_count=1)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        class FailingAnalyzer:
            async def run(self, input: dict, **kwargs) -> dict:
                raise RuntimeError("Agent exploded")

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_qdrant(),
            patch(
                "pipeline.engine.orchestrator.PaperAnalyzerAgent",
                return_value=FailingAnalyzer(),
            ),
        ):
            await run_pipeline(job_id, jobs_dir)

        status = await read_status(job_id, jobs_dir)
        assert status is not None
        assert status.status == JobState.FAILED
        assert status.error is not None
        assert "pipeline failed" in status.error.lower()

        event_types = [e.event_type for e in events]
        assert EventType.JOB_FAILED in event_types

    async def test_judge_gate_quarantine(self, jobs_dir: Path):
        """If the judge gate quarantines, status is QUARANTINED, not COMPLETED/FAILED,
        and review.yaml is still written (quarantine flags content, doesn't hide it)."""
        job_id, _ = _create_test_job(jobs_dir, paper_count=1)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_qdrant(),
            _patch_paper_analyzer(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
            patch(
                "pipeline.engine.orchestrator.score_review",
                return_value=JudgeGateResult(
                    verdict="quarantine",
                    reason="judge gate failed rubric item(s): faithfulness",
                    scores={"faithfulness": 0.2, "citation_accuracy": 0.85},
                ),
            ),
        ):
            await run_pipeline(job_id, jobs_dir)

        status = await read_status(job_id, jobs_dir)
        assert status is not None
        assert status.status == JobState.QUARANTINED
        assert status.quarantine_reason is not None
        assert "faithfulness" in status.quarantine_reason

        job_path = jobs_dir / job_id
        assert (job_path / "review.yaml").exists()
        review = await read_yaml(job_path / "review.yaml")
        assert review is not None

        event_types = [e.event_type for e in events]
        assert EventType.REVIEW_QUARANTINED in event_types
        assert EventType.REVIEW_GENERATED not in event_types
        assert EventType.JOB_COMPLETED not in event_types
