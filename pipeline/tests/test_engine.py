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
    StubClaimExtractor,
    StubThemeDedup,
    StubThemeExtractor,
    StubThemeReviewer,
)
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
        assert isinstance(StubThemeExtractor(), Agent)
        assert isinstance(StubClaimExtractor(), Agent)
        assert isinstance(StubThemeDedup(), Agent)
        assert isinstance(StubThemeReviewer(), Agent)
        assert isinstance(StubAggregator(), Agent)

    async def test_theme_extractor_output(self):
        agent = StubThemeExtractor()
        result = await agent.run({"paper_id": "p1", "title": "My Paper", "content": "text"})
        assert "themes" in result
        assert len(result["themes"]) == 1
        theme = result["themes"][0]
        assert "id" in theme
        assert "label" in theme
        assert theme["paper_id"] == "p1"

    async def test_claim_extractor_output(self):
        agent = StubClaimExtractor()
        result = await agent.run({"paper_id": "p1", "title": "My Paper", "content": "text"})
        assert "claims" in result
        assert len(result["claims"]) == 1
        claim = result["claims"][0]
        assert "id" in claim
        assert "text" in claim
        assert claim["source"]["paper_id"] == "p1"

    async def test_theme_dedup_output(self):
        agent = StubThemeDedup()
        themes = [
            {"id": "t1", "label": "Theme 1", "description": "desc1", "paper_id": "p1"},
            {"id": "t2", "label": "Theme 2", "description": "desc2", "paper_id": "p2"},
        ]
        result = await agent.run({"themes": themes})
        assert "theme_map" in result
        assert "themes" in result
        assert len(result["themes"]) == 2

    async def test_theme_reviewer_output(self):
        agent = StubThemeReviewer()
        theme = {"id": "t1", "label": "Theme 1"}
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
            Stage.THEME_EXTRACTION,
            Stage.CLAIM_EXTRACTION,
            Stage.THEME_DEDUP,
            Stage.THEME_REVIEW,
            Stage.AGGREGATION,
        ]

    def test_stage_values(self):
        assert Stage.THEME_EXTRACTION == "theme_extraction"
        assert Stage.AGGREGATION == "aggregation"


# ---------------------------------------------------------------------------
# Full Pipeline Tests
# ---------------------------------------------------------------------------


def _patch_theme_extractor():
    """Patch ThemeExtractorAgent with StubThemeExtractor in orchestrator."""
    return patch(
        "pipeline.engine.orchestrator.ThemeExtractorAgent",
        return_value=StubThemeExtractor(),
    )


def _patch_claim_extractor():
    """Patch ClaimExtractorAgent with StubClaimExtractor in orchestrator."""
    return patch(
        "pipeline.engine.orchestrator.ClaimExtractorAgent",
        return_value=StubClaimExtractor(),
    )


def _patch_theme_dedup():
    """Patch ThemeDedupAgent with StubThemeDedup in orchestrator."""
    return patch(
        "pipeline.engine.orchestrator.ThemeDedupAgent",
        return_value=StubThemeDedup(),
    )


def _patch_theme_reviewer():
    """Patch ThemeReviewerAgent with StubThemeReviewer in orchestrator."""
    return patch(
        "pipeline.engine.orchestrator.ThemeReviewerAgent",
        return_value=StubThemeReviewer(),
    )


def _patch_aggregator():
    """Patch AggregatorAgent with StubAggregator in orchestrator."""
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
            _patch_theme_extractor(),
            _patch_claim_extractor(),
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
        """Stages execute in correct order: theme_extraction → claim_extraction → dedup → review → aggregation."""
        job_id, _ = _create_test_job(jobs_dir, paper_count=2)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_theme_extractor(),
            _patch_claim_extractor(),
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
            Stage.THEME_EXTRACTION,
            Stage.CLAIM_EXTRACTION,
            Stage.THEME_DEDUP,
            Stage.THEME_REVIEW,
            Stage.AGGREGATION,
        ]

    async def test_sync_barriers(self, jobs_dir: Path):
        """Theme dedup starts only after both theme and claim extraction complete."""
        job_id, _ = _create_test_job(jobs_dir, paper_count=3)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_theme_extractor(),
            _patch_claim_extractor(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        event_types = [e.event_type for e in events]

        # Find positions of key events
        claim_complete_positions = [
            i
            for i, e in enumerate(events)
            if e.event_type == EventType.STAGE_COMPLETED
            and e.payload.get("stage") == Stage.CLAIM_EXTRACTION
        ]
        dedup_start_positions = [
            i
            for i, e in enumerate(events)
            if e.event_type == EventType.STAGE_STARTED
            and e.payload.get("stage") == Stage.THEME_DEDUP
        ]

        assert len(claim_complete_positions) >= 1
        assert len(dedup_start_positions) == 1
        # Dedup starts after claim extraction completes
        assert dedup_start_positions[0] > claim_complete_positions[-1]

    async def test_parallel_per_paper_stages(self, jobs_dir: Path):
        """All papers are processed in parallel stages."""
        job_id, paper_ids = _create_test_job(jobs_dir, paper_count=3)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_theme_extractor(),
            _patch_claim_extractor(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        # Check theme extraction processed all papers
        theme_events = [
            e
            for e in events
            if e.event_type == EventType.THEME_EXTRACTED
        ]
        assert len(theme_events) == 3

        # Check claim extraction processed all papers
        claim_events = [
            e
            for e in events
            if e.event_type == EventType.CLAIM_EXTRACTED
        ]
        assert len(claim_events) == 3

    async def test_progress_events_emitted(self, jobs_dir: Path):
        """Progress events report correct completed/total counts."""
        job_id, paper_ids = _create_test_job(jobs_dir, paper_count=3)
        emitter = EventEmitter(job_id, jobs_dir)
        events = _collect_events(emitter)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_theme_extractor(),
            _patch_claim_extractor(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        # Find PAPER_PROCESSED events for theme_extraction stage
        progress_events = [
            e
            for e in events
            if e.event_type == EventType.PAPER_PROCESSED
            and e.payload.get("stage") == Stage.THEME_EXTRACTION
        ]
        # With 3 papers, 2 emit PAPER_PROCESSED (the 3rd emits STAGE_COMPLETED)
        assert len(progress_events) == 2
        totals = [e.payload["total"] for e in progress_events]
        assert all(t == 3 for t in totals)

    async def test_persistence_artifacts(self, jobs_dir: Path):
        """Pipeline writes all expected intermediate files."""
        job_id, paper_ids = _create_test_job(jobs_dir, paper_count=2)
        emitter = EventEmitter(job_id, jobs_dir)

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            _patch_theme_extractor(),
            _patch_claim_extractor(),
            _patch_theme_dedup(),
            _patch_theme_reviewer(),
            _patch_aggregator(),
        ):
            await run_pipeline(job_id, jobs_dir)

        job_path = jobs_dir / job_id

        # Per-paper theme files
        for pid in paper_ids:
            assert (job_path / "themes" / f"{pid}.yaml").exists()
            assert (job_path / "claims" / f"{pid}.yaml").exists()

        # Theme map
        assert (job_path / "theme_map.yaml").exists()

        # Theme reviews (one per theme = one per paper in stubs)
        theme_reviews = list((job_path / "theme_reviews").iterdir())
        assert len(theme_reviews) == 2

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
            _patch_theme_extractor(),
            _patch_claim_extractor(),
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

        class FailingExtractor:
            async def run(self, input: dict) -> dict:
                raise RuntimeError("Agent exploded")

        with (
            patch("pipeline.engine.orchestrator.get_or_create_emitter", return_value=emitter),
            patch(
                "pipeline.engine.orchestrator.ThemeExtractorAgent",
                return_value=FailingExtractor(),
            ),
        ):
            await run_pipeline(job_id, jobs_dir)

        status = await read_status(job_id, jobs_dir)
        assert status is not None
        assert status.status == JobState.FAILED
        assert "Agent exploded" in (status.error or "")

        event_types = [e.event_type for e in events]
        assert EventType.JOB_FAILED in event_types


# ---------------------------------------------------------------------------
# API Integration Test
# ---------------------------------------------------------------------------


class TestAPILaunchesPipeline:
    async def test_create_job_launches_pipeline(self, tmp_path: Path):
        """POST /jobs launches the pipeline as a background task."""
        from unittest.mock import patch

        from httpx import ASGITransport, AsyncClient

        from pipeline.app import app
        from pipeline.config import settings

        jobs_dir = tmp_path / "jobs"
        jobs_dir.mkdir()

        def _make_pdf_bytes() -> bytes:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            buf = BytesIO()
            c = canvas.Canvas(buf, pagesize=letter)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, 700, "Test Paper Title")
            c.setFont("Helvetica", 12)
            c.drawString(100, 680, "Author One, Author Two")
            c.drawString(100, 640, "This is the abstract of the test paper.")
            c.drawString(100, 620, "It contains enough text to pass quality checks.")
            for i in range(20):
                c.drawString(100, 590 - i * 15, f"Paragraph {i}: Lorem ipsum dolor sit amet.")
            c.showPage()
            c.save()
            buf.seek(0)
            return buf.read()

        pdf_bytes = _make_pdf_bytes()

        with patch.object(settings, "jobs_dir", str(jobs_dir)), _patch_theme_extractor(), _patch_claim_extractor(), _patch_theme_dedup(), _patch_theme_reviewer(), _patch_aggregator():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/jobs",
                    files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
                )
                assert resp.status_code == 201
                job_id = resp.json()["job_id"]

                # Give the background task time to complete
                await asyncio.sleep(0.5)

                # Check that pipeline ran
                status_resp = await client.get(f"/jobs/{job_id}/status")
                assert status_resp.status_code == 200
                status = status_resp.json()
                assert status["status"] in ("completed", "running")
