"""Filesystem persistence: job directories, YAML state, NDJSON read-back."""

from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from .events import Event
from .models import JobStatus

_locks: dict[str, asyncio.Lock] = {}


def _get_lock(job_id: str) -> asyncio.Lock:
    if job_id not in _locks:
        _locks[job_id] = asyncio.Lock()
    return _locks[job_id]


JOB_SUBDIRS = ("themes", "claims", "theme_reviews")


def create_job_dir(job_id: str, jobs_dir: Path) -> Path:
    """Create the full job directory tree. Returns the job directory path."""
    job_path = jobs_dir / job_id
    job_path.mkdir(parents=True, exist_ok=True)
    for subdir in JOB_SUBDIRS:
        (job_path / subdir).mkdir(exist_ok=True)
    return job_path


async def write_yaml(path: Path, data: dict, job_id: str | None = None) -> None:
    """Write data dict to a YAML file. Acquires per-job lock if job_id given."""

    def _sync() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    if job_id:
        async with _get_lock(job_id):
            await asyncio.to_thread(_sync)
    else:
        await asyncio.to_thread(_sync)


async def read_yaml(path: Path) -> dict | None:
    """Read a YAML file. Returns None if file doesn't exist."""

    def _sync() -> dict | None:
        if not path.exists():
            return None
        with open(path) as f:
            return yaml.safe_load(f)

    return await asyncio.to_thread(_sync)


async def write_status(job_id: str, status: JobStatus, jobs_dir: Path) -> None:
    """Serialize JobStatus to status.yaml."""
    path = jobs_dir / job_id / "status.yaml"
    data = status.model_dump(mode="json")
    await write_yaml(path, data, job_id=job_id)


async def read_status(job_id: str, jobs_dir: Path) -> JobStatus | None:
    """Deserialize status.yaml to JobStatus. Returns None if missing."""
    path = jobs_dir / job_id / "status.yaml"
    data = await read_yaml(path)
    if data is None:
        return None
    return JobStatus.model_validate(data)


async def read_events(
    job_id: str, jobs_dir: Path, after_event_id: str | None = None
) -> list[Event]:
    """Read events from NDJSON file. Optionally filter to events after a given ID."""
    path = jobs_dir / job_id / "events.ndjson"

    def _sync() -> list[Event]:
        if not path.exists():
            return []
        events: list[Event] = []
        found_marker = after_event_id is None
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                event = Event.model_validate_json(stripped)
                if not found_marker:
                    if event.event_id == after_event_id:
                        found_marker = True
                    continue
                events.append(event)
        return events

    return await asyncio.to_thread(_sync)
