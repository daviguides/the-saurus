"""Pydantic models for pipeline job state."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class JobState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(BaseModel):
    """Top-level job status persisted to status.yaml."""

    job_id: str
    status: JobState = JobState.PENDING
    stage: str = ""
    progress: float = 0.0
    paper_count: int = 0
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class PaperEntry(BaseModel):
    """Single paper record persisted in papers.yaml list."""

    paper_id: str
    filename: str
    title: str = ""
    page_count: int = 0
    ingested_at: datetime | None = Field(default=None)
