"""Tests for pipeline test client Pydantic schemas."""

from datetime import datetime, timezone

import pytest

from pipeline_test_client.schemas import (
    CreateJobResponse,
    EnrichedPaper,
    Event,
    EventType,
    EventsResponse,
    HealthResponse,
    JobState,
    JobStatus,
    PapersResponse,
    ReviewResponse,
    TestCase,
    TestStep,
)


class TestEventType:
    def test_all_event_types_are_strings(self):
        for et in EventType:
            assert isinstance(et.value, str)

    def test_job_lifecycle_events(self):
        assert EventType.JOB_CREATED == "job_created"
        assert EventType.JOB_STARTED == "job_started"
        assert EventType.JOB_COMPLETED == "job_completed"
        assert EventType.JOB_FAILED == "job_failed"

    def test_agent_events(self):
        assert EventType.AGENT_STARTED == "agent_started"
        assert EventType.AGENT_COMPLETED == "agent_completed"
        assert EventType.AGENT_ERROR == "agent_error"


class TestEvent:
    def test_create_event(self):
        event = Event(
            event_id="abc-123",
            event_type="job_created",
            timestamp=datetime.now(timezone.utc),
            job_id="job-456",
            payload={"paper_count": 2},
        )
        assert event.event_id == "abc-123"
        assert event.event_type == "job_created"
        assert event.job_id == "job-456"
        assert event.payload["paper_count"] == 2

    def test_event_default_payload(self):
        event = Event(
            event_id="x",
            event_type="test",
            timestamp=datetime.now(timezone.utc),
            job_id="j",
        )
        assert event.payload == {}

    def test_event_roundtrip(self):
        event = Event(
            event_id="rt-1",
            event_type=EventType.STAGE_STARTED,
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            job_id="job-rt",
            payload={"stage": "paper_analysis"},
        )
        data = event.model_dump(mode="json")
        restored = Event.model_validate(data)
        assert restored.event_id == event.event_id
        assert restored.event_type == event.event_type
        assert restored.payload == event.payload


class TestJobStatus:
    def test_create_status(self):
        now = datetime.now(timezone.utc)
        status = JobStatus(
            job_id="j-1",
            status=JobState.RUNNING,
            stage="paper_analysis",
            progress=0.25,
            paper_count=3,
            created_at=now,
            updated_at=now,
        )
        assert status.status == JobState.RUNNING
        assert status.progress == 0.25

    def test_default_values(self):
        now = datetime.now(timezone.utc)
        status = JobStatus(job_id="j-2", created_at=now, updated_at=now)
        assert status.status == JobState.PENDING
        assert status.stage == ""
        assert status.progress == 0.0
        assert status.error is None


class TestCreateJobResponse:
    def test_create(self):
        resp = CreateJobResponse(job_id="j-1", paper_count=2, status="pending")
        assert resp.job_id == "j-1"
        assert resp.paper_count == 2


class TestEnrichedPaper:
    def test_with_themes_and_claims(self):
        paper = EnrichedPaper(
            paper_id="p-1",
            filename="test.pdf",
            title="Test Paper",
            authors=["Alice", "Bob"],
            page_count=10,
            themes=[{"name": "ML", "description": "Machine learning"}],
            claims=[{"text": "Models improve accuracy"}],
        )
        assert len(paper.themes) == 1
        assert len(paper.claims) == 1

    def test_defaults(self):
        paper = EnrichedPaper(paper_id="p-2", filename="f.pdf")
        assert paper.title == ""
        assert paper.authors == []
        assert paper.themes == []
        assert paper.claims == []


class TestPapersResponse:
    def test_empty(self):
        resp = PapersResponse(papers=[])
        assert len(resp.papers) == 0


class TestReviewResponse:
    def test_with_sections(self):
        resp = ReviewResponse(review={
            "title": "Literature Review",
            "sections": [
                {"heading": "Introduction", "body": "This review..."},
            ],
        })
        assert resp.review["title"] == "Literature Review"
        assert len(resp.review["sections"]) == 1


class TestHealthResponse:
    def test_create(self):
        resp = HealthResponse(status="ok", service="pipeline")
        assert resp.status == "ok"


class TestEventsResponse:
    def test_with_events(self):
        now = datetime.now(timezone.utc)
        resp = EventsResponse(events=[
            Event(event_id="e1", event_type="job_created", timestamp=now, job_id="j1"),
        ])
        assert len(resp.events) == 1


class TestTestCase:
    def test_parse_yaml_structure(self):
        tc = TestCase(
            name="Basic Flow",
            description="Test basic pipeline",
            timeout_seconds=120,
            files=[{"path": "sample.pdf"}],
            steps=[
                TestStep(action="upload"),
                TestStep(action="wait_complete", expect_status="completed"),
                TestStep(action="check_papers", expect_paper_count=1, expect_theme_count_min=3),
            ],
        )
        assert tc.name == "Basic Flow"
        assert len(tc.steps) == 3
        assert tc.steps[1].expect_status == "completed"
        assert tc.steps[2].expect_paper_count == 1

    def test_defaults(self):
        tc = TestCase(name="Minimal")
        assert tc.timeout_seconds == 300.0
        assert tc.files == []
        assert tc.steps == []

    def test_step_defaults(self):
        step = TestStep(action="upload")
        assert step.expect_status is None
        assert step.expect_paper_count is None
        assert step.expect_review_has_citations is None
