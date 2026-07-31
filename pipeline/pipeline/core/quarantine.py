"""Shared quarantine mechanism: flag a job for manual review instead of
silently rejecting or silently serving its output.

One mechanism, multiple triggers (design doc §7.4/§8.2) — this task builds
it for the post-aggregation LLM-as-Judge gate; a later toxic-content gate
reuses the same function with its own reason string.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .events import EventEmitter, EventType
from .models import JobState, JobStatus
from .persistence import write_status


async def quarantine_job(
    job_id: str,
    jobs_dir: Path,
    emitter: EventEmitter,
    *,
    created_at: datetime,
    paper_count: int,
    stage: str,
    reason: str,
) -> None:
    """Mark a job QUARANTINED and emit REVIEW_QUARANTINED.

    Unlike a failure, the job's output (review.yaml) is left in place —
    quarantine flags content for a human to look at, it doesn't hide it.
    """
    now = datetime.now(UTC)
    status = JobStatus(
        job_id=job_id,
        status=JobState.QUARANTINED,
        stage=stage,
        progress=1.0,
        paper_count=paper_count,
        created_at=created_at,
        updated_at=now,
        quarantine_reason=reason,
    )
    await write_status(job_id, status, jobs_dir)
    await emitter.emit(EventType.REVIEW_QUARANTINED, {"reason": reason})
