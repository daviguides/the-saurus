"""Run the pipeline against golden test PDFs and capture outputs.

Calls the pipeline REST API to process the golden PDFs,
waits for completion, then saves outputs for evaluation.

Usage:
    uv run python -m pipeline.golden.run_pipeline

Requires:
    Pipeline service running on localhost:8002
"""

import asyncio
import json
import time
from pathlib import Path

import httpx

GOLDEN_DIR = Path(__file__).parent
PAPERS_DIR = GOLDEN_DIR / "papers"
OUTPUTS_DIR = GOLDEN_DIR / "outputs"
PIPELINE_URL = "http://localhost:8002"
POLL_INTERVAL = 5  # seconds
MAX_WAIT = 600  # 10 minutes


async def run():
    """Upload golden PDFs, wait for pipeline, save outputs."""
    OUTPUTS_DIR.mkdir(exist_ok=True)

    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs in {PAPERS_DIR}")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Upload PDFs
        files = [
            ("files", (p.name, p.read_bytes(), "application/pdf"))
            for p in pdf_files
        ]
        print(f"Uploading {len(files)} PDFs to {PIPELINE_URL}/jobs")
        resp = await client.post(f"{PIPELINE_URL}/jobs", files=files)
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        print(f"Job created: {job_id}")

        # Poll for completion
        start = time.time()
        while time.time() - start < MAX_WAIT:
            status_resp = await client.get(
                f"{PIPELINE_URL}/jobs/{job_id}/status",
            )
            status = status_resp.json()
            state = status.get("status", "")
            progress = status.get("progress", 0)
            stage = status.get("stage", "")

            print(
                f"  [{state}] stage={stage} "
                f"progress={progress:.0%} "
                f"elapsed={time.time() - start:.0f}s"
            )

            if state == "completed":
                break
            if state == "failed":
                print(f"Pipeline failed: {status.get('error', 'unknown')}")
                return

            await asyncio.sleep(POLL_INTERVAL)
        else:
            print(f"Timed out after {MAX_WAIT}s")
            return

        # Fetch and save outputs
        papers_resp = await client.get(
            f"{PIPELINE_URL}/jobs/{job_id}/papers",
        )
        papers_data = papers_resp.json()
        (OUTPUTS_DIR / "papers.json").write_text(
            json.dumps(papers_data, indent=2, ensure_ascii=False),
        )

        review_resp = await client.get(
            f"{PIPELINE_URL}/jobs/{job_id}/review",
        )
        review_data = review_resp.json()
        (OUTPUTS_DIR / "review.json").write_text(
            json.dumps(review_data, indent=2, ensure_ascii=False),
        )

        events_resp = await client.get(
            f"{PIPELINE_URL}/jobs/{job_id}/events",
        )
        events_data = events_resp.json()
        (OUTPUTS_DIR / "events.json").write_text(
            json.dumps(events_data, indent=2, ensure_ascii=False),
        )

        print(f"Outputs saved to {OUTPUTS_DIR}/")
        print(f"  papers.json: {len(papers_data.get('papers', []))} papers")
        review = review_data.get("review", {})
        print(f"  review.json: {review.get('title', 'untitled')}")
        print(f"  events.json: {len(events_data.get('events', []))} events")


if __name__ == "__main__":
    asyncio.run(run())
