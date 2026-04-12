"""REST API routes for pipeline job management."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile

from pipeline.config import settings
from pipeline.engine import run_pipeline
from pipeline.core import (
    EventEmitter,
    EventType,
    JobState,
    JobStatus,
    PaperEntry,
    create_job_dir,
    read_events,
    read_status,
    read_yaml,
    write_status,
    write_yaml,
)
from pipeline.ingestion import IngestionError, ingest_pdf
from pipeline.ws.stream import register_emitter

from .schemas import (
    CreateJobResponse,
    EnrichedPaper,
    EventsResponse,
    HealthResponse,
    PapersResponse,
    ReviewResponse,
    StatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB

_running_tasks: dict[str, asyncio.Task] = {}


def _jobs_dir() -> Path:
    return Path(settings.jobs_dir)


def _get_job_dir(job_id: str) -> Path:
    path = _jobs_dir() / job_id
    if not path.resolve().is_relative_to(_jobs_dir().resolve()):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Job not found")
    return path


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="pipeline")


@router.post("/jobs", response_model=CreateJobResponse, status_code=201)
async def create_job(files: list[UploadFile]) -> CreateJobResponse:
    if not files:
        raise HTTPException(status_code=422, detail="No files provided")

    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files accepted, got: {f.filename}",
            )

    job_id = str(uuid4())
    jobs_dir = _jobs_dir()
    job_path = create_job_dir(job_id, jobs_dir)

    # Create events file and emitter
    (job_path / "events.ndjson").touch()
    emitter = EventEmitter(job_id, jobs_dir)
    register_emitter(job_id, emitter)

    # Ingest PDFs
    papers: list[PaperEntry] = []
    now = datetime.now(UTC)

    for f in files:
        pdf_bytes = await f.read()
        if len(pdf_bytes) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File {f.filename} exceeds 50 MB limit",
            )

        # Save raw PDF — sanitize filename to prevent path traversal
        safe_name = PurePosixPath(f.filename).name
        pdf_path = job_path / safe_name
        pdf_path.write_bytes(pdf_bytes)

        try:
            result = ingest_pdf(pdf_bytes)
        except IngestionError as exc:
            logger.warning("Ingestion failed for %s: %s", f.filename, exc)
            continue

        paper_id = str(uuid4())
        papers.append(
            PaperEntry(
                paper_id=paper_id,
                filename=f.filename,
                title=result.title,
                authors=result.authors,
                page_count=result.page_count,
                ingested_at=now,
            )
        )

        # Save markdown
        md_path = job_path / f"{paper_id}.md"
        md_path.write_text(result.to_annotated_markdown())

    if not papers:
        raise HTTPException(status_code=400, detail="No papers could be ingested")

    # Write papers.yaml
    await write_yaml(
        job_path / "papers.yaml",
        [p.model_dump(mode="json") for p in papers],
        job_id=job_id,
    )

    # Write status.yaml
    status = JobStatus(
        job_id=job_id,
        status=JobState.PENDING,
        paper_count=len(papers),
        created_at=now,
        updated_at=now,
    )
    await write_status(job_id, status, jobs_dir)

    # Emit job_created event
    await emitter.emit(
        EventType.JOB_CREATED,
        {"paper_count": len(papers), "filenames": [p.filename for p in papers]},
    )

    # Launch pipeline as background task
    task = asyncio.create_task(run_pipeline(job_id, jobs_dir))
    _running_tasks[job_id] = task
    task.add_done_callback(lambda t: _running_tasks.pop(job_id, None))

    return CreateJobResponse(
        job_id=job_id,
        paper_count=len(papers),
        status=JobState.PENDING,
    )


@router.get("/jobs/{job_id}/status", response_model=StatusResponse)
async def get_status(job_id: str) -> StatusResponse:
    _get_job_dir(job_id)
    status = await read_status(job_id, _jobs_dir())
    if status is None:
        raise HTTPException(status_code=404, detail="Job status not found")
    return StatusResponse.model_validate(status.model_dump())


@router.get("/jobs/{job_id}/events", response_model=EventsResponse)
async def get_events(job_id: str, after_event_id: str | None = None) -> EventsResponse:
    _get_job_dir(job_id)
    events = await read_events(job_id, _jobs_dir(), after_event_id=after_event_id)
    return EventsResponse(events=events)


@router.get("/jobs/{job_id}/papers", response_model=PapersResponse)
async def get_papers(job_id: str) -> PapersResponse:
    job_path = _get_job_dir(job_id)
    data = await read_yaml(job_path / "papers.yaml")
    if data is None:
        return PapersResponse(papers=[])
    papers = [PaperEntry.model_validate(p) for p in data]

    # Enrich each paper with themes and claims from per-paper YAML files
    enriched: list[EnrichedPaper] = []
    for paper in papers:
        themes_data = await read_yaml(job_path / "themes" / f"{paper.paper_id}.yaml")
        claims_data = await read_yaml(job_path / "claims" / f"{paper.paper_id}.yaml")
        enriched.append(
            EnrichedPaper(
                paper_id=paper.paper_id,
                filename=paper.filename,
                title=paper.title,
                authors=paper.authors,
                page_count=paper.page_count,
                themes=themes_data.get("themes", []) if themes_data else [],
                claims=claims_data.get("claims", []) if claims_data else [],
            )
        )
    return PapersResponse(papers=enriched)


@router.get("/jobs/{job_id}/review", response_model=ReviewResponse)
async def get_review(job_id: str) -> ReviewResponse:
    _get_job_dir(job_id)
    data = await read_yaml(_jobs_dir() / job_id / "review.yaml")
    if data is None:
        raise HTTPException(status_code=404, detail="Review not yet generated")
    return ReviewResponse(review=data)
