"""Tests for WebSocket event streaming."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from pipeline.app import app
from pipeline.config import settings
from pipeline.core.events import EventEmitter, EventType
from pipeline.ws.stream import (
    _emitters,
    clear_all_emitters,
    get_or_create_emitter,
    register_emitter,
    remove_emitter,
)


@pytest.fixture(autouse=True)
def _clean_emitters():
    """Ensure emitter registry is clean before and after each test."""
    clear_all_emitters()
    yield
    clear_all_emitters()


@pytest.fixture
def jobs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "jobs"
    d.mkdir()
    return d


@pytest.fixture
def _patch_dirs(jobs_dir: Path):
    with patch.object(settings, "jobs_dir", str(jobs_dir)):
        yield


@pytest.fixture
def _patch_no_auth():
    with patch.object(settings, "api_key", None):
        yield


@pytest.fixture
def _patch_with_auth():
    with patch.object(settings, "api_key", "test-secret"):
        yield


def _make_job_dir(jobs_dir: Path, job_id: str = "test-job") -> Path:
    """Create a minimal job directory with events file."""
    job_path = jobs_dir / job_id
    job_path.mkdir(parents=True, exist_ok=True)
    (job_path / "events.ndjson").touch()
    return job_path


class TestEmitterRegistry:
    """Test emitter registration and cleanup."""

    def test_register_and_retrieve(self, tmp_path: Path) -> None:
        """Registered emitter is retrievable."""
        emitter = EventEmitter("job-1", tmp_path)
        register_emitter("job-1", emitter)
        assert _emitters["job-1"] is emitter

    def test_get_or_create_creates_new(self, tmp_path: Path) -> None:
        """get_or_create creates emitter if not registered."""
        assert "new-job" not in _emitters
        emitter = get_or_create_emitter("new-job", tmp_path)
        assert "new-job" in _emitters
        assert _emitters["new-job"] is emitter

    def test_get_or_create_returns_existing(self, tmp_path: Path) -> None:
        """get_or_create returns existing emitter if already registered."""
        original = EventEmitter("job-2", tmp_path)
        register_emitter("job-2", original)
        retrieved = get_or_create_emitter("job-2", tmp_path)
        assert retrieved is original

    def test_remove_emitter_cleans_up(self, tmp_path: Path) -> None:
        """remove_emitter removes from registry."""
        emitter = EventEmitter("job-3", tmp_path)
        register_emitter("job-3", emitter)
        assert "job-3" in _emitters
        remove_emitter("job-3")
        assert "job-3" not in _emitters

    def test_remove_nonexistent_is_noop(self) -> None:
        """Removing non-registered job_id does not raise."""
        remove_emitter("does-not-exist")  # should not raise


class TestWebSocketStream:
    """Test WebSocket event delivery."""

    def test_connects_to_valid_job(self, _patch_dirs, _patch_no_auth, jobs_dir: Path) -> None:
        """WebSocket connects successfully for existing job."""
        _make_job_dir(jobs_dir, "ws-job-1")
        client = TestClient(app)
        with client.websocket_connect("/jobs/ws-job-1/stream"):
            pass  # Connection accepted — close immediately

    def test_rejects_invalid_job(self, _patch_dirs, _patch_no_auth) -> None:
        """WebSocket rejects connection for nonexistent job."""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/jobs/nonexistent/stream"):
                pass

    def test_receives_live_events(self, _patch_dirs, _patch_no_auth, jobs_dir: Path) -> None:
        """Connected client receives events emitted after connection."""
        job_id = "ws-job-live"
        _make_job_dir(jobs_dir, job_id)
        emitter = EventEmitter(job_id, jobs_dir)
        register_emitter(job_id, emitter)

        client = TestClient(app)
        with client.websocket_connect(f"/jobs/{job_id}/stream") as ws:
            # Emit an event from a background thread (emitter.emit is async)
            def emit_event():
                loop = asyncio.new_event_loop()
                loop.run_until_complete(
                    emitter.emit(EventType.JOB_STARTED, {"msg": "hello"})
                )
                loop.close()

            t = threading.Thread(target=emit_event)
            t.start()
            t.join(timeout=5)

            data = ws.receive_json(mode="text")
            assert data["event_type"] == "job_started"
            assert data["job_id"] == job_id
            assert data["payload"]["msg"] == "hello"

    def test_receives_multiple_events(self, _patch_dirs, _patch_no_auth, jobs_dir: Path) -> None:
        """Connected client receives multiple events in order."""
        job_id = "ws-job-multi"
        _make_job_dir(jobs_dir, job_id)
        emitter = EventEmitter(job_id, jobs_dir)
        register_emitter(job_id, emitter)

        client = TestClient(app)
        with client.websocket_connect(f"/jobs/{job_id}/stream") as ws:
            def emit_events():
                loop = asyncio.new_event_loop()
                loop.run_until_complete(
                    emitter.emit(EventType.STAGE_STARTED, {"stage": "analysis"})
                )
                loop.run_until_complete(
                    emitter.emit(EventType.STAGE_COMPLETED, {"stage": "analysis"})
                )
                loop.close()

            t = threading.Thread(target=emit_events)
            t.start()
            t.join(timeout=5)

            ev1 = ws.receive_json(mode="text")
            ev2 = ws.receive_json(mode="text")
            assert ev1["event_type"] == "stage_started"
            assert ev2["event_type"] == "stage_completed"

    def test_auth_required_when_configured(self, _patch_dirs, _patch_with_auth) -> None:
        """WebSocket rejects without token when api_key is set."""
        client = TestClient(app)
        # No token provided — should be rejected
        with pytest.raises(Exception):
            with client.websocket_connect("/jobs/any-job/stream"):
                pass

    def test_auth_accepts_valid_token(
        self, _patch_dirs, _patch_with_auth, jobs_dir: Path
    ) -> None:
        """WebSocket accepts with correct token when api_key is set."""
        _make_job_dir(jobs_dir, "auth-job")
        client = TestClient(app)
        with client.websocket_connect("/jobs/auth-job/stream?token=test-secret"):
            pass  # Connection accepted

    def test_auth_not_required_when_unconfigured(
        self, _patch_dirs, _patch_no_auth, jobs_dir: Path
    ) -> None:
        """WebSocket accepts without token when api_key is not set."""
        _make_job_dir(jobs_dir, "noauth-job")
        client = TestClient(app)
        with client.websocket_connect("/jobs/noauth-job/stream"):
            pass  # Connection accepted
