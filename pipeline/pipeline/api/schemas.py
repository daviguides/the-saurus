"""Pydantic response models for the pipeline REST API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from pipeline.core import Event, JobStatus, PaperEntry


class CreateJobResponse(BaseModel):
    job_id: str
    paper_count: int
    status: str


class StatusResponse(JobStatus):
    pass


class EventsResponse(BaseModel):
    events: list[Event]


class EnrichedPaper(BaseModel):
    """Paper with merged themes and claims from pipeline output."""

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
