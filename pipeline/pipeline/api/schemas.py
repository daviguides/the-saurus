"""Pydantic response models for the pipeline REST API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from pipeline.core import Event, JobStatus, PaperEntry


class CreateJobResponse(BaseModel):
    job_id: str
    paper_count: int
    status: str


class StatusResponse(JobStatus):
    pass


class EventsResponse(BaseModel):
    events: list[Event]


class PapersResponse(BaseModel):
    papers: list[PaperEntry]


class ReviewResponse(BaseModel):
    review: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    service: str
