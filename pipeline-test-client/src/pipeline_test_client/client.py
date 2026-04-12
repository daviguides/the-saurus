"""HTTP + WebSocket client for the pipeline service."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Coroutine
from pathlib import Path
from typing import Any

import httpx
import websockets

from .schemas import (
    CreateJobResponse,
    Event,
    EventType,
    HealthResponse,
    JobStatus,
    PapersResponse,
    ReviewResponse,
)


class PipelineError(Exception):
    """Raised when the pipeline API returns an error."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class PipelineClient:
    """Async client for the pipeline REST API and WebSocket stream."""

    def __init__(self, base_url: str = "http://localhost:8002", timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> PipelineClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    def _raise_for_error(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise PipelineError(resp.status_code, detail)

    # --- REST endpoints ---

    async def health(self) -> HealthResponse:
        resp = await self._http.get("/health")
        self._raise_for_error(resp)
        return HealthResponse.model_validate(resp.json())

    async def upload_pdfs(self, files: list[Path]) -> CreateJobResponse:
        """Upload PDF files and start the pipeline. Returns the job creation response."""
        upload_files = []
        for f in files:
            upload_files.append(("files", (f.name, f.read_bytes(), "application/pdf")))
        resp = await self._http.post("/jobs", files=upload_files)
        self._raise_for_error(resp)
        return CreateJobResponse.model_validate(resp.json())

    async def get_status(self, job_id: str) -> JobStatus:
        resp = await self._http.get(f"/jobs/{job_id}/status")
        self._raise_for_error(resp)
        return JobStatus.model_validate(resp.json())

    async def get_papers(self, job_id: str) -> PapersResponse:
        resp = await self._http.get(f"/jobs/{job_id}/papers")
        self._raise_for_error(resp)
        return PapersResponse.model_validate(resp.json())

    async def get_review(self, job_id: str) -> ReviewResponse:
        resp = await self._http.get(f"/jobs/{job_id}/review")
        self._raise_for_error(resp)
        return ReviewResponse.model_validate(resp.json())

    # --- WebSocket streaming ---

    async def stream_events(
        self,
        job_id: str,
        callback: Callable[[Event], Coroutine[Any, Any, None]] | None = None,
    ) -> AsyncIterator[Event]:
        """Connect to the WebSocket stream and yield events.

        If a callback is provided, it will be called for each event in addition
        to yielding. The stream ends when a job_completed or job_failed event
        is received.
        """
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/jobs/{job_id}/stream"

        async for ws in websockets.connect(ws_url, close_timeout=5):
            try:
                async for raw in ws:
                    data = json.loads(raw)
                    event = Event.model_validate(data)

                    if callback:
                        await callback(event)

                    yield event

                    if event.event_type in (
                        EventType.JOB_COMPLETED,
                        EventType.JOB_FAILED,
                    ):
                        return
            except websockets.ConnectionClosed:
                return

    async def run_full_pipeline(
        self,
        files: list[Path],
        callback: Callable[[Event], Coroutine[Any, Any, None]] | None = None,
    ) -> dict[str, Any]:
        """Upload files, stream events until completion, then return the review.

        Returns a dict with keys: job_id, status, review, papers.
        """
        job = await self.upload_pdfs(files)
        job_id = job.job_id

        final_event_type: str | None = None
        async for event in self.stream_events(job_id, callback=callback):
            final_event_type = event.event_type

        status = await self.get_status(job_id)

        result: dict[str, Any] = {
            "job_id": job_id,
            "status": status.model_dump(mode="json"),
        }

        if final_event_type == EventType.JOB_COMPLETED:
            try:
                review_resp = await self.get_review(job_id)
                result["review"] = review_resp.review
            except PipelineError:
                result["review"] = None

            try:
                papers_resp = await self.get_papers(job_id)
                result["papers"] = [p.model_dump(mode="json") for p in papers_resp.papers]
            except PipelineError:
                result["papers"] = []

        return result

    # --- Polling helpers ---

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 2.0,
        timeout: float | None = None,
    ) -> JobStatus:
        """Poll the status endpoint until the job completes or fails."""
        effective_timeout = timeout or self.timeout
        elapsed = 0.0
        while elapsed < effective_timeout:
            status = await self.get_status(job_id)
            if status.status in ("completed", "failed"):
                return status
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(f"Job {job_id} did not complete within {effective_timeout}s")
