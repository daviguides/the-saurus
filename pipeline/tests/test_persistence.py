"""Tests for persistence: directory creation, YAML round-trip, event read-back."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pipeline.core import (
    JobState,
    JobStatus,
    create_job_dir,
    read_events,
    read_status,
    read_yaml,
    write_status,
    write_yaml,
)
from pipeline.core.events import Event


@pytest.fixture
def jobs_dir(tmp_path: Path) -> Path:
    return tmp_path / "jobs"


class TestCreateJobDir:
    def test_creates_full_tree(self, jobs_dir: Path):
        path = create_job_dir("job-1", jobs_dir)
        assert path == jobs_dir / "job-1"
        assert path.is_dir()
        assert (path / "themes").is_dir()
        assert (path / "claims").is_dir()
        assert (path / "theme_reviews").is_dir()

    def test_idempotent(self, jobs_dir: Path):
        create_job_dir("job-1", jobs_dir)
        create_job_dir("job-1", jobs_dir)
        assert (jobs_dir / "job-1").is_dir()


class TestYamlRoundTrip:
    async def test_write_read(self, jobs_dir: Path):
        path = jobs_dir / "test.yaml"
        data = {"key": "value", "nested": {"a": 1, "b": [2, 3]}}
        await write_yaml(path, data)
        result = await read_yaml(path)
        assert result == data

    async def test_read_missing_returns_none(self, jobs_dir: Path):
        result = await read_yaml(jobs_dir / "nonexistent.yaml")
        assert result is None

    async def test_write_with_lock(self, jobs_dir: Path):
        path = jobs_dir / "locked.yaml"
        data = {"x": 42}
        await write_yaml(path, data, job_id="job-lock")
        result = await read_yaml(path)
        assert result == data


class TestStatusRoundTrip:
    async def test_write_read_status(self, jobs_dir: Path):
        create_job_dir("job-s", jobs_dir)
        now = datetime.now(UTC)
        status = JobStatus(
            job_id="job-s",
            status=JobState.RUNNING,
            stage="ingestion",
            progress=0.5,
            paper_count=10,
            created_at=now,
            updated_at=now,
        )
        await write_status("job-s", status, jobs_dir)
        result = await read_status("job-s", jobs_dir)
        assert result is not None
        assert result.job_id == "job-s"
        assert result.status == JobState.RUNNING
        assert result.progress == 0.5
        assert result.paper_count == 10

    async def test_read_status_missing(self, jobs_dir: Path):
        result = await read_status("nonexistent", jobs_dir)
        assert result is None


class TestReadEvents:
    async def test_read_empty(self, jobs_dir: Path):
        create_job_dir("job-e", jobs_dir)
        events = await read_events("job-e", jobs_dir)
        assert events == []

    async def test_read_missing_dir(self, jobs_dir: Path):
        events = await read_events("nonexistent", jobs_dir)
        assert events == []

    async def test_read_events(self, jobs_dir: Path):
        create_job_dir("job-e2", jobs_dir)
        ndjson = jobs_dir / "job-e2" / "events.ndjson"
        e1 = Event(event_type="job_started", job_id="job-e2")
        e2 = Event(event_type="paper_ingested", job_id="job-e2", payload={"p": 1})
        ndjson.write_text(e1.model_dump_json() + "\n" + e2.model_dump_json() + "\n")

        events = await read_events("job-e2", jobs_dir)
        assert len(events) == 2
        assert events[0].event_type == "job_started"
        assert events[1].event_type == "paper_ingested"
        assert events[1].payload == {"p": 1}

    async def test_after_event_id_filter(self, jobs_dir: Path):
        create_job_dir("job-e3", jobs_dir)
        ndjson = jobs_dir / "job-e3" / "events.ndjson"
        e1 = Event(event_id="aaa", event_type="a", job_id="job-e3")
        e2 = Event(event_id="bbb", event_type="b", job_id="job-e3")
        e3 = Event(event_id="ccc", event_type="c", job_id="job-e3")
        ndjson.write_text(
            e1.model_dump_json() + "\n"
            + e2.model_dump_json() + "\n"
            + e3.model_dump_json() + "\n"
        )

        events = await read_events("job-e3", jobs_dir, after_event_id="aaa")
        assert len(events) == 2
        assert events[0].event_id == "bbb"
        assert events[1].event_id == "ccc"
