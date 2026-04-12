"""Progress tracking for pipeline execution."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from pipeline.core import EventEmitter, EventType, JobState, JobStatus, write_status

from .stages import TOTAL_STAGES


class ProgressTracker:
    """Tracks stage and overall pipeline progress with lock-protected counters."""

    def __init__(
        self,
        job_id: str,
        jobs_dir: Path,
        emitter: EventEmitter,
        paper_count: int,
    ) -> None:
        self.job_id = job_id
        self.jobs_dir = jobs_dir
        self.emitter = emitter
        self.paper_count = paper_count
        self._completed_stages = 0
        self._stage_counter = 0
        self._stage_total = 0
        self._lock = asyncio.Lock()
        self._created_at = datetime.now(UTC)

    def _overall_progress(self) -> float:
        if TOTAL_STAGES == 0:
            return 1.0
        stage_frac = (
            self._stage_counter / self._stage_total if self._stage_total > 0 else 0.0
        )
        return (self._completed_stages + stage_frac) / TOTAL_STAGES

    async def _update_status(self, stage: str, state: JobState) -> None:
        status = JobStatus(
            job_id=self.job_id,
            status=state,
            stage=stage,
            progress=self._overall_progress(),
            paper_count=self.paper_count,
            created_at=self._created_at,
            updated_at=datetime.now(UTC),
        )
        await write_status(self.job_id, status, self.jobs_dir)

    async def stage_start(self, stage: str, total: int) -> None:
        """Mark a stage as started. total = number of items (papers or themes)."""
        self._stage_counter = 0
        self._stage_total = total
        await self._update_status(stage, JobState.RUNNING)
        await self.emitter.emit(
            EventType.STAGE_STARTED,
            {"stage": stage, "total": total},
        )

    async def stage_item_done(self, stage: str, item_id: str) -> None:
        """Increment progress counter for one item in a parallel stage."""
        async with self._lock:
            self._stage_counter += 1
            completed = self._stage_counter
        await self._update_status(stage, JobState.RUNNING)
        # C5: Don't emit STAGE_COMPLETED here — let stage_complete handle it
        await self.emitter.emit(
            EventType.PAPER_PROCESSED,
            {
                "stage": stage,
                "item_id": item_id,
                "completed": completed,
                "total": self._stage_total,
                "progress": self._overall_progress(),
            },
        )

    async def stage_complete(self, stage: str) -> None:
        """Mark a stage as fully completed."""
        self._completed_stages += 1
        self._stage_counter = 0
        self._stage_total = 0
        await self._update_status(stage, JobState.RUNNING)
        await self.emitter.emit(
            EventType.STAGE_COMPLETED,
            {"stage": stage, "progress": self._overall_progress()},
        )
