"""REST API routes for pipeline job management."""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, UploadFile

from pipeline.config import settings
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
from pipeline.engine import run_pipeline
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
MAX_FILE_COUNT = 50  # S2: upper bound on number of uploaded files

_running_tasks: dict[str, asyncio.Task] = {}


def get_running_tasks() -> dict[str, asyncio.Task]:
    """Expose running tasks for lifespan shutdown cleanup."""
    return _running_tasks


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

    # S2: Limit number of uploaded files
    if len(files) > MAX_FILE_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: {len(files)} exceeds limit of {MAX_FILE_COUNT}",
        )

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
        # S1: Read in chunks with a size cap to avoid unbounded memory usage
        chunks: list[bytes] = []
        total_size = 0
        while True:
            chunk = await f.read(1024 * 1024)  # 1 MB chunks
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_PDF_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File {f.filename} exceeds 50 MB limit",
                )
            chunks.append(chunk)
        pdf_bytes = b"".join(chunks)

        # S5: Validate PDF magic bytes
        if not pdf_bytes[:5].startswith(b"%PDF-"):
            logger.warning("Skipping %s: invalid PDF magic bytes", f.filename)
            continue

        # Save raw PDF — sanitize filename to prevent path traversal
        safe_name = PurePosixPath(f.filename).name
        pdf_path = job_path / safe_name
        # S4: Handle duplicate filenames with counter suffix
        counter = 1
        while pdf_path.exists():
            stem = PurePosixPath(safe_name).stem
            suffix = PurePosixPath(safe_name).suffix
            pdf_path = job_path / f"{stem}_{counter}{suffix}"
            counter += 1
        await asyncio.to_thread(pdf_path.write_bytes, pdf_bytes)

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
        await asyncio.to_thread(md_path.write_text, result.to_annotated_markdown())

    if not papers:
        # E1: Clean up orphan PDF files when ingestion fails for all files
        shutil.rmtree(job_path, ignore_errors=True)
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

    # B1: Check if job_id already running before creating a new task
    if job_id in _running_tasks and not _running_tasks[job_id].done():
        raise HTTPException(status_code=409, detail="Job is already running")

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
async def get_events(
    job_id: str,
    after_event_id: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
) -> EventsResponse:
    _get_job_dir(job_id)
    events = await read_events(job_id, _jobs_dir(), after_event_id=after_event_id)
    events = events[:limit]
    return EventsResponse(events=events)


@router.get("/jobs/{job_id}/papers", response_model=PapersResponse)
async def get_papers(job_id: str) -> PapersResponse:
    job_path = _get_job_dir(job_id)
    data = await read_yaml(job_path / "papers.yaml")
    if data is None:
        return PapersResponse(papers=[])
    papers = [PaperEntry.model_validate(p) for p in data]

    # Enrich each paper with themes and claims from per-paper YAML files
    # Read all YAML files in a single parallel gather to avoid sequential I/O
    theme_coros = [read_yaml(job_path / "themes" / f"{p.paper_id}.yaml") for p in papers]
    claim_coros = [read_yaml(job_path / "claims" / f"{p.paper_id}.yaml") for p in papers]
    all_results = await asyncio.gather(*theme_coros, *claim_coros)
    all_themes_data = all_results[: len(papers)]
    all_claims_data = all_results[len(papers) :]

    enriched: list[EnrichedPaper] = []
    for paper, themes_data, claims_data in zip(papers, all_themes_data, all_claims_data):
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
