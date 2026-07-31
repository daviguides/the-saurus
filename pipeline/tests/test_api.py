"""Tests for REST API endpoints and WebSocket streaming."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from pipeline.app import app
from pipeline.config import settings


def _make_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 700, "Test Paper Title")
    c.setFont("Helvetica", 12)
    c.drawString(100, 680, "Author One, Author Two")
    c.drawString(100, 640, "This is the abstract of the test paper.")
    c.drawString(100, 620, "It contains enough text to pass quality checks.")
    # Add more text to exceed quality threshold
    for i in range(20):
        c.drawString(100, 590 - i * 15, f"Paragraph {i}: Lorem ipsum dolor sit amet.")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


@pytest.fixture
def pdf_bytes() -> bytes:
    return _make_pdf_bytes()


@pytest.fixture
def jobs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "jobs"
    d.mkdir()
    return d


@pytest.fixture
def _patch_jobs_dir(jobs_dir: Path):
    with patch.object(settings, "jobs_dir", str(jobs_dir)):
        yield


@pytest.fixture
async def client(_patch_jobs_dir) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "pipeline"


class TestCreateJob:
    async def test_create_job(self, client: AsyncClient, pdf_bytes: bytes):
        resp = await client.post(
            "/jobs",
            files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "job_id" in data
        assert data["paper_count"] == 1
        assert data["status"] == "pending"

    async def test_create_job_multiple_pdfs(self, client: AsyncClient, pdf_bytes: bytes):
        resp = await client.post(
            "/jobs",
            files=[
                ("files", ("paper1.pdf", pdf_bytes, "application/pdf")),
                ("files", ("paper2.pdf", pdf_bytes, "application/pdf")),
            ],
        )
        assert resp.status_code == 201
        assert resp.json()["paper_count"] == 2

    async def test_create_job_no_files(self, client: AsyncClient):
        resp = await client.post("/jobs", files=[])
        assert resp.status_code == 422

    async def test_create_job_non_pdf(self, client: AsyncClient):
        resp = await client.post(
            "/jobs",
            files=[("files", ("test.txt", b"hello", "text/plain"))],
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]


class TestChunkTrigger:
    """Validate the size-triggered chunking gate in the upload route."""

    async def test_default_threshold_writes_single_markdown(
        self, client: AsyncClient, pdf_bytes: bytes, jobs_dir: Path,
    ):
        create_resp = await client.post(
            "/jobs",
            files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
        )
        job_id = create_resp.json()["job_id"]
        job_path = jobs_dir / job_id

        md_files = sorted(job_path.glob("*.md"))
        assert len(md_files) == 1
        assert not list(job_path.glob("*__chunk*.md"))

    async def test_low_threshold_writes_chunk_files(
        self, client: AsyncClient, pdf_bytes: bytes, jobs_dir: Path,
    ):
        with patch.object(settings, "chunk_token_threshold", 1):
            create_resp = await client.post(
                "/jobs",
                files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
            )
        job_id = create_resp.json()["job_id"]
        job_path = jobs_dir / job_id

        md_files = set(job_path.glob("*.md"))
        chunk_files = set(job_path.glob("*__chunk*.md"))
        assert len(chunk_files) >= 1
        assert md_files == chunk_files  # every .md file is a chunk, no bare single file


class TestGetStatus:
    async def test_get_status(self, client: AsyncClient, pdf_bytes: bytes):
        create_resp = await client.post(
            "/jobs",
            files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
        )
        job_id = create_resp.json()["job_id"]

        resp = await client.get(f"/jobs/{job_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        assert data["paper_count"] == 1

    async def test_get_status_not_found(self, client: AsyncClient):
        resp = await client.get("/jobs/nonexistent/status")
        assert resp.status_code == 404


class TestGetEvents:
    async def test_get_events(self, client: AsyncClient, pdf_bytes: bytes):
        create_resp = await client.post(
            "/jobs",
            files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
        )
        job_id = create_resp.json()["job_id"]

        resp = await client.get(f"/jobs/{job_id}/events")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) >= 1
        assert events[0]["event_type"] == "job_created"

    async def test_get_events_after_id(self, client: AsyncClient, pdf_bytes: bytes):
        create_resp = await client.post(
            "/jobs",
            files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
        )
        job_id = create_resp.json()["job_id"]

        # Get all events to find the first event_id
        resp = await client.get(f"/jobs/{job_id}/events")
        first_id = resp.json()["events"][0]["event_id"]

        # Fetch events after the first one (should be empty)
        resp = await client.get(f"/jobs/{job_id}/events?after_event_id={first_id}")
        assert resp.status_code == 200
        assert len(resp.json()["events"]) == 0

    async def test_get_events_not_found(self, client: AsyncClient):
        resp = await client.get("/jobs/nonexistent/events")
        assert resp.status_code == 404


class TestGetPapers:
    async def test_get_papers(self, client: AsyncClient, pdf_bytes: bytes):
        create_resp = await client.post(
            "/jobs",
            files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
        )
        job_id = create_resp.json()["job_id"]

        resp = await client.get(f"/jobs/{job_id}/papers")
        assert resp.status_code == 200
        papers = resp.json()["papers"]
        assert len(papers) == 1
        assert papers[0]["filename"] == "test.pdf"
        assert papers[0]["page_count"] >= 1

    async def test_get_papers_not_found(self, client: AsyncClient):
        resp = await client.get("/jobs/nonexistent/papers")
        assert resp.status_code == 404


class TestGetReview:
    async def test_get_review_not_ready(self, client: AsyncClient, pdf_bytes: bytes):
        create_resp = await client.post(
            "/jobs",
            files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
        )
        job_id = create_resp.json()["job_id"]

        resp = await client.get(f"/jobs/{job_id}/review")
        assert resp.status_code == 404
        assert "not yet generated" in resp.json()["detail"]

    async def test_get_review_not_found(self, client: AsyncClient):
        resp = await client.get("/jobs/nonexistent/review")
        assert resp.status_code == 404


class TestWebSocket:
    def test_ws_job_not_found(self, _patch_jobs_dir):
        from starlette.testclient import TestClient

        sync_client = TestClient(app)
        with pytest.raises(Exception):
            with sync_client.websocket_connect("/jobs/nonexistent/stream"):
                pass

    def test_ws_connects_to_existing_job(self, _patch_jobs_dir, pdf_bytes: bytes):
        """Test that WebSocket successfully connects to an existing job."""
        from starlette.testclient import TestClient

        sync_client = TestClient(app)

        # Create a job via REST first
        create_resp = sync_client.post(
            "/jobs",
            files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
        )
        assert create_resp.status_code == 201
        job_id = create_resp.json()["job_id"]

        # WebSocket connects and accepts (validates handshake works)
        with sync_client.websocket_connect(f"/jobs/{job_id}/stream"):
            pass  # Connection accepted — close immediately
