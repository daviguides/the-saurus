"""FastAPI application for the pipeline service."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from pipeline.api import router
from pipeline.api.routes import get_running_tasks
from pipeline.config import settings
from pipeline.core import JobState, JobStatus, read_status, write_status
from pipeline.core.qdrant import close_indexer
from pipeline.ws import websocket_stream

logger = logging.getLogger(__name__)


async def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Verify API key if configured. No-op when api_key is not set."""
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _recover_orphan_jobs(jobs_dir: Path) -> None:
    """Mark any jobs stuck in 'running' or 'pending' as failed on startup.

    When the server restarts, in-memory asyncio tasks are lost.
    Jobs left in running state are orphans that will never complete.
    """
    if not jobs_dir.is_dir():
        return

    count = 0
    for job_path in jobs_dir.iterdir():
        if not job_path.is_dir():
            continue
        job_id = job_path.name
        status = await read_status(job_id, jobs_dir)
        if status and status.status in (JobState.RUNNING, JobState.PENDING):
            now = datetime.now(UTC)
            failed_status = JobStatus(
                job_id=job_id,
                status=JobState.FAILED,
                stage=status.stage or "",
                progress=status.progress,
                paper_count=status.paper_count,
                created_at=status.created_at or now,
                updated_at=now,
                error="Pipeline server restarted — job was interrupted. Upload again to retry.",
            )
            await write_status(job_id, failed_status, jobs_dir)
            count += 1
            logger.info(
                "Recovered orphan job %s (was %s at stage %s)",
                job_id, status.status, status.stage,
            )

    if count:
        logger.info("Recovered %d orphan job(s)", count)


@asynccontextmanager
async def lifespan(app: FastAPI):
    jobs_dir = Path(settings.jobs_dir)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    await _recover_orphan_jobs(jobs_dir)
    yield
    # E2/R2: Cancel running tasks on shutdown
    running = get_running_tasks()
    for job_id, task in list(running.items()):
        if not task.done():
            task.cancel()
            logger.info("Cancelled running task for job %s", job_id)
    # Wait briefly for tasks to finish cancellation
    if running:
        await asyncio.gather(*running.values(), return_exceptions=True)
        running.clear()
    # R1: Close Qdrant client
    close_indexer()


app = FastAPI(
    title="The Saurus Pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, dependencies=[Depends(verify_api_key)])


@app.websocket("/jobs/{job_id}/stream")
async def ws_stream(
    websocket: WebSocket, job_id: str, token: str | None = Query(None)
) -> None:
    if settings.api_key and token != settings.api_key:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    await websocket_stream(websocket, job_id, Path(settings.jobs_dir))
