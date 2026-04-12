"""Security tests for pipeline API."""

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


@pytest.fixture
async def authed_client(_patch_jobs_dir) -> AsyncClient:
    """Client with auth enabled and correct key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAuthentication:
    """Test opt-in API key authentication."""

    async def test_no_auth_when_key_not_configured(self, _patch_jobs_dir):
        """Endpoints are open when PIPELINE_API_KEY is not set."""
        with patch.object(settings, "api_key", None):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health")
                assert resp.status_code == 200

    async def test_rejects_without_key_when_configured(self, _patch_jobs_dir):
        """Endpoints return 401 when key is required but not provided."""
        with patch.object(settings, "api_key", "test-secret-key"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health")
                assert resp.status_code == 401
                assert resp.json()["detail"] == "Unauthorized"

    async def test_rejects_wrong_key(self, _patch_jobs_dir):
        """Endpoints return 401 with incorrect key."""
        with patch.object(settings, "api_key", "test-secret-key"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health", headers={"x-api-key": "wrong-key"})
                assert resp.status_code == 401

    async def test_accepts_correct_key(self, _patch_jobs_dir):
        """Endpoints succeed with correct key."""
        with patch.object(settings, "api_key", "test-secret-key"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health", headers={"x-api-key": "test-secret-key"})
                assert resp.status_code == 200


class TestUploadValidation:
    """Test upload security."""

    async def test_rejects_non_pdf_magic_bytes(self, client: AsyncClient):
        """Files with .pdf extension but wrong magic bytes are skipped."""
        fake_pdf = b"NOT-A-PDF-FILE-CONTENT-HERE"
        resp = await client.post(
            "/jobs",
            files=[("files", ("fake.pdf", fake_pdf, "application/pdf"))],
        )
        # All files skipped -> "No papers could be ingested"
        assert resp.status_code == 400
        assert "No papers could be ingested" in resp.json()["detail"]

    async def test_path_traversal_in_job_id(self, jobs_dir: Path):
        """Crafted job_id with ../ is rejected by _get_job_dir guard."""
        from fastapi import HTTPException
        from pipeline.api.routes import _get_job_dir

        # Create a directory outside jobs_dir that a traversal could reach
        outside = jobs_dir.parent / "secret"
        outside.mkdir()

        # Directly test the guard function with a traversal job_id
        with pytest.raises(HTTPException) as exc_info:
            _get_job_dir("../secret")
        assert exc_info.value.status_code == 400
        assert "Invalid job ID" in exc_info.value.detail

    async def test_oversized_file_returns_413(self, client: AsyncClient):
        """Files exceeding 50MB return 413."""
        # Create a file just over 50MB with valid PDF header
        oversized = b"%PDF-1.4" + b"\x00" * (50 * 1024 * 1024 + 1)
        resp = await client.post(
            "/jobs",
            files=[("files", ("big.pdf", oversized, "application/pdf"))],
        )
        assert resp.status_code == 413
        assert "50 MB" in resp.json()["detail"]

    async def test_too_many_files_returns_400(self, client: AsyncClient, pdf_bytes: bytes):
        """More than 50 files returns 400."""
        files = [("files", (f"paper_{i}.pdf", pdf_bytes, "application/pdf")) for i in range(51)]
        resp = await client.post("/jobs", files=files)
        assert resp.status_code == 400
        assert "Too many files" in resp.json()["detail"]
