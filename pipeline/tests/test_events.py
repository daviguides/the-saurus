"""Tests for event schema, emitter NDJSON append, and listener broadcast."""

import json
from pathlib import Path

import pytest

from pipeline.core import Event, EventEmitter, EventType
from pipeline.core.persistence import create_job_dir


@pytest.fixture
def jobs_dir(tmp_path: Path) -> Path:
    return tmp_path / "jobs"


class TestEventModel:
    def test_defaults(self):
        e = Event(event_type="job_started", job_id="j1")
        assert e.event_id  # auto-generated uuid
        assert e.timestamp  # auto-generated
        assert e.payload == {}

    def test_json_round_trip(self):
        e = Event(event_type="paper_ingested", job_id="j1", payload={"k": "v"})
        raw = e.model_dump_json()
        restored = Event.model_validate_json(raw)
        assert restored.event_id == e.event_id
        assert restored.event_type == e.event_type
        assert restored.payload == {"k": "v"}

    def test_event_type_enum(self):
        e = Event(event_type=EventType.JOB_CREATED, job_id="j1")
        assert e.event_type == "job_created"


class TestEventEmitter:
    async def test_emit_appends_ndjson(self, jobs_dir: Path):
        create_job_dir("j1", jobs_dir)
        # Create empty ndjson file
        ndjson = jobs_dir / "j1" / "events.ndjson"
        ndjson.touch()

        emitter = EventEmitter("j1", jobs_dir)
        event = await emitter.emit(EventType.JOB_STARTED)

        lines = ndjson.read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_type"] == "job_started"
        assert parsed["event_id"] == event.event_id

    async def test_emit_multiple(self, jobs_dir: Path):
        create_job_dir("j2", jobs_dir)
        (jobs_dir / "j2" / "events.ndjson").touch()

        emitter = EventEmitter("j2", jobs_dir)
        await emitter.emit(EventType.JOB_STARTED)
        await emitter.emit(EventType.PAPER_INGESTED, {"paper_id": "p1"})

        lines = (jobs_dir / "j2" / "events.ndjson").read_text().strip().split("\n")
        assert len(lines) == 2

    async def test_broadcasts_to_listeners(self, jobs_dir: Path):
        create_job_dir("j3", jobs_dir)
        (jobs_dir / "j3" / "events.ndjson").touch()

        received: list[Event] = []

        async def listener(event: Event) -> None:
            received.append(event)

        emitter = EventEmitter("j3", jobs_dir)
        emitter.add_listener(listener)
        event = await emitter.emit(EventType.STAGE_STARTED, {"stage": "ingestion"})

        assert len(received) == 1
        assert received[0].event_id == event.event_id

    async def test_listener_exception_does_not_crash(self, jobs_dir: Path):
        create_job_dir("j4", jobs_dir)
        (jobs_dir / "j4" / "events.ndjson").touch()

        async def bad_listener(event: Event) -> None:
            raise RuntimeError("boom")

        good_received: list[Event] = []

        async def good_listener(event: Event) -> None:
            good_received.append(event)

        emitter = EventEmitter("j4", jobs_dir)
        emitter.add_listener(bad_listener)
        emitter.add_listener(good_listener)

        # Should not raise
        event = await emitter.emit(EventType.JOB_COMPLETED)
        assert len(good_received) == 1

    async def test_remove_listener(self, jobs_dir: Path):
        create_job_dir("j5", jobs_dir)
        (jobs_dir / "j5" / "events.ndjson").touch()

        received: list[Event] = []

        async def listener(event: Event) -> None:
            received.append(event)

        emitter = EventEmitter("j5", jobs_dir)
        emitter.add_listener(listener)
        await emitter.emit(EventType.JOB_STARTED)
        assert len(received) == 1

        emitter.remove_listener(listener)
        await emitter.emit(EventType.JOB_COMPLETED)
        assert len(received) == 1  # no new events

    async def test_emit_returns_event(self, jobs_dir: Path):
        create_job_dir("j6", jobs_dir)
        (jobs_dir / "j6" / "events.ndjson").touch()

        emitter = EventEmitter("j6", jobs_dir)
        event = await emitter.emit(EventType.JOB_CREATED, {"test": True})
        assert event.event_type == "job_created"
        assert event.job_id == "j6"
        assert event.payload == {"test": True}
