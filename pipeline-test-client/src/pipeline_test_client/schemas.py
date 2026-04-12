"""Pydantic models mirroring the pipeline event types and response schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# --- Event types ---


class EventType(StrEnum):
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    PAPER_INGESTED = "paper_ingested"
    PAPER_PROCESSED = "paper_processed"
    PAPER_ANALYZED = "paper_analyzed"
    THEME_EXTRACTED = "theme_extracted"
    THEME_DEDUPLICATED = "theme_deduplicated"
    CLAIM_EXTRACTED = "claim_extracted"
    REVIEW_GENERATED = "review_generated"
    AGENT_STARTED = "agent_started"
    AGENT_TOOL_CALL = "agent_tool_call"
    AGENT_TOOL_RESULT = "agent_tool_result"
    AGENT_CONTENT = "agent_content"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"


class Event(BaseModel):
    """Single pipeline event received via WebSocket or REST."""

    event_id: str
    event_type: str
    timestamp: datetime
    job_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


# --- Job status ---


class JobState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(BaseModel):
    job_id: str
    status: JobState = JobState.PENDING
    stage: str = ""
    progress: float = 0.0
    paper_count: int = 0
    created_at: datetime
    updated_at: datetime
    error: str | None = None


# --- API responses ---


class CreateJobResponse(BaseModel):
    job_id: str
    paper_count: int
    status: str


class EnrichedPaper(BaseModel):
    paper_id: str
    filename: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    page_count: int = 0
    themes: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)


class PapersResponse(BaseModel):
    papers: list[EnrichedPaper]


class ReviewResponse(BaseModel):
    review: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    service: str


class EventsResponse(BaseModel):
    events: list[Event]


# --- Test case schema ---


class TestStep(BaseModel):
    action: str  # upload | wait_complete | check_status | check_review | check_papers
    expect_status: str | None = None
    expect_paper_count: int | None = None
    expect_theme_count_min: int | None = None
    expect_claim_count_min: int | None = None
    expect_review_sections_min: int | None = None
    expect_review_has_citations: bool | None = None


class TestCase(BaseModel):
    name: str
    description: str = ""
    timeout_seconds: float = 300.0
    files: list[dict[str, str]] = Field(default_factory=list)
    steps: list[TestStep] = Field(default_factory=list)
