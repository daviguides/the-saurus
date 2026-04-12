"""Typer CLI for the pipeline test client."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from .client import PipelineClient, PipelineError
from .handlers import EventHandler, PapersHandler, ProgressHandler, ReviewHandler, console
from .schemas import TestCase, TestStep

app = typer.Typer(
    name="pipeline-test",
    help="CLI tool for testing The Saurus pipeline API.",
    rich_markup_mode="rich",
)

# Global options stored via callback
_state: dict = {"url": "http://localhost:8002", "timeout": 300.0, "verbose": False}

CASES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cases"


@app.callback()
def main(
    url: Annotated[str, typer.Option("--url", "-u", help="Pipeline server URL")] = "http://localhost:8002",
    timeout: Annotated[float, typer.Option("--timeout", "-t", help="Timeout in seconds")] = 300.0,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show all event details")] = False,
) -> None:
    """Pipeline test client -- test The Saurus pipeline REST API + WebSocket streaming."""
    _state["url"] = url
    _state["timeout"] = timeout
    _state["verbose"] = verbose


def _client() -> PipelineClient:
    return PipelineClient(base_url=_state["url"], timeout=_state["timeout"])


def _run(coro):
    """Run an async coroutine."""
    return asyncio.run(coro)


# --- Commands ---


@app.command()
def upload(
    pdf_paths: Annotated[list[Path], typer.Argument(help="PDF files to upload")],
) -> None:
    """Upload PDFs and start the pipeline. Prints the job_id."""

    async def _upload():
        for p in pdf_paths:
            if not p.exists():
                console.print(f"[red]File not found: {p}[/red]")
                raise typer.Exit(1)

        async with _client() as client:
            result = await client.upload_pdfs(pdf_paths)
            console.print(Panel(f"[bold green]Job created[/bold green]\n\n"
                                f"  job_id:      {result.job_id}\n"
                                f"  papers:      {result.paper_count}\n"
                                f"  status:      {result.status}"))
            # Print just the job_id to stdout for piping
            print(result.job_id)

    _run(_upload())


@app.command()
def status(
    job_id: Annotated[str, typer.Argument(help="Job ID to check")],
) -> None:
    """Check the status of a pipeline job."""

    async def _status():
        async with _client() as client:
            try:
                s = await client.get_status(job_id)
            except PipelineError as e:
                console.print(f"[red]{e}[/red]")
                raise typer.Exit(1)

            color = {
                "pending": "yellow",
                "running": "blue",
                "completed": "green",
                "failed": "red",
            }.get(s.status, "white")

            console.print(Panel(
                f"[bold]Job Status[/bold]\n\n"
                f"  job_id:      {s.job_id}\n"
                f"  status:      [{color}]{s.status}[/{color}]\n"
                f"  stage:       {s.stage or '-'}\n"
                f"  progress:    {s.progress:.0%}\n"
                f"  papers:      {s.paper_count}\n"
                f"  created:     {s.created_at}\n"
                f"  updated:     {s.updated_at}\n"
                + (f"  error:       [red]{s.error}[/red]\n" if s.error else ""),
            ))

    _run(_status())


@app.command()
def stream(
    job_id: Annotated[str, typer.Argument(help="Job ID to stream events for")],
) -> None:
    """Connect to WebSocket and display live pipeline events."""

    async def _stream():
        handler = EventHandler(verbose=_state["verbose"])
        async with _client() as client:
            console.print(f"[dim]Streaming events for job {job_id}...[/dim]\n")
            try:
                async for _event in client.stream_events(job_id, callback=handler.handle):
                    pass
            except Exception as e:
                console.print(f"[red]Stream error: {e}[/red]")
                raise typer.Exit(1)
        console.print("\n[dim]Stream ended.[/dim]")

    _run(_stream())


@app.command()
def review(
    job_id: Annotated[str, typer.Argument(help="Job ID to fetch review for")],
) -> None:
    """Fetch and display the generated literature review."""

    async def _review():
        async with _client() as client:
            try:
                resp = await client.get_review(job_id)
            except PipelineError as e:
                console.print(f"[red]{e}[/red]")
                raise typer.Exit(1)
            ReviewHandler.display(resp.review)

    _run(_review())


@app.command()
def papers(
    job_id: Annotated[str, typer.Argument(help="Job ID to fetch papers for")],
) -> None:
    """Fetch and display extracted papers with themes and claims."""

    async def _papers():
        async with _client() as client:
            try:
                resp = await client.get_papers(job_id)
            except PipelineError as e:
                console.print(f"[red]{e}[/red]")
                raise typer.Exit(1)
            PapersHandler.display(resp)

    _run(_papers())


@app.command()
def run(
    pdf_paths: Annotated[list[Path], typer.Argument(help="PDF files to upload")],
) -> None:
    """Full flow: upload PDFs, stream events, then show the review."""

    async def _run_flow():
        for p in pdf_paths:
            if not p.exists():
                console.print(f"[red]File not found: {p}[/red]")
                raise typer.Exit(1)

        handler = EventHandler(verbose=_state["verbose"])

        async with _client() as client:
            console.print("[bold]Uploading PDFs...[/bold]")
            result = await client.run_full_pipeline(pdf_paths, callback=handler.handle)

            job_id = result["job_id"]
            status_data = result["status"]

            console.print()
            if status_data.get("status") == "completed":
                console.print(Panel(f"[bold green]Pipeline completed[/bold green] -- job_id: {job_id}"))

                if result.get("review"):
                    ReviewHandler.display(result["review"])

                if result.get("papers"):
                    from .schemas import PapersResponse, EnrichedPaper
                    papers_resp = PapersResponse(
                        papers=[EnrichedPaper.model_validate(p) for p in result["papers"]]
                    )
                    PapersHandler.display(papers_resp)
            else:
                console.print(Panel(
                    f"[bold red]Pipeline {status_data.get('status', 'unknown')}[/bold red]\n"
                    f"job_id: {job_id}\n"
                    f"error: {status_data.get('error', 'N/A')}",
                    style="red",
                ))
                raise typer.Exit(1)

    _run(_run_flow())


@app.command(name="test-flow")
def test_flow(
    case: Annotated[str, typer.Argument(help="Test case name (without .yaml) or path to YAML file")],
) -> None:
    """Run a YAML test case with assertions against the pipeline."""

    async def _test():
        # Resolve test case file
        case_path = Path(case)
        if not case_path.exists():
            case_path = CASES_DIR / f"{case}.yaml"
        if not case_path.exists():
            console.print(f"[red]Test case not found: {case}[/red]")
            console.print(f"[dim]Looked in: {CASES_DIR}[/dim]")
            raise typer.Exit(1)

        with open(case_path) as f:
            raw = yaml.safe_load(f)

        tc = TestCase.model_validate(raw)
        console.print(Panel(f"[bold]{tc.name}[/bold]\n{tc.description}", title="Test Case"))

        # Resolve file paths relative to the case file's directory
        pdf_files: list[Path] = []
        case_dir = case_path.parent
        data_dir = case_dir.parent  # data/ directory
        for file_spec in tc.files:
            p = Path(file_spec["path"])
            if not p.is_absolute():
                # Try relative to case file dir, then data/ dir
                if (case_dir / p).exists():
                    p = case_dir / p
                elif (data_dir / p).exists():
                    p = data_dir / p
            if not p.exists():
                console.print(f"[red]Test file not found: {file_spec['path']}[/red]")
                console.print("[dim]Place PDF files in the data/ directory[/dim]")
                raise typer.Exit(1)
            pdf_files.append(p)

        job_id: str | None = None
        passed = 0
        failed = 0

        async with _client() as client:
            for step in tc.steps:
                console.print(f"\n[bold]Step: {step.action}[/bold]")

                try:
                    if step.action == "upload":
                        result = await client.upload_pdfs(pdf_files)
                        job_id = result.job_id
                        console.print(f"  job_id: {job_id}")
                        console.print(f"  papers: {result.paper_count}")
                        passed += 1

                    elif step.action == "wait_complete":
                        if not job_id:
                            console.print("[red]  No job_id -- run upload first[/red]")
                            failed += 1
                            continue

                        s = await client.wait_for_completion(
                            job_id, timeout=tc.timeout_seconds
                        )
                        if step.expect_status and s.status != step.expect_status:
                            console.print(
                                f"[red]  FAIL: expected status={step.expect_status}, "
                                f"got {s.status}[/red]"
                            )
                            failed += 1
                        else:
                            console.print(f"  [green]OK[/green] status={s.status}")
                            passed += 1

                    elif step.action == "check_status":
                        if not job_id:
                            console.print("[red]  No job_id[/red]")
                            failed += 1
                            continue

                        s = await client.get_status(job_id)
                        ok = True
                        if step.expect_status and s.status != step.expect_status:
                            console.print(
                                f"[red]  FAIL: expected status={step.expect_status}, "
                                f"got {s.status}[/red]"
                            )
                            ok = False

                        if ok:
                            console.print(f"  [green]OK[/green] status={s.status}")
                            passed += 1
                        else:
                            failed += 1

                    elif step.action == "check_papers":
                        if not job_id:
                            console.print("[red]  No job_id[/red]")
                            failed += 1
                            continue

                        resp = await client.get_papers(job_id)
                        ok = True

                        if step.expect_paper_count is not None:
                            actual = len(resp.papers)
                            if actual != step.expect_paper_count:
                                console.print(
                                    f"[red]  FAIL: expected {step.expect_paper_count} "
                                    f"papers, got {actual}[/red]"
                                )
                                ok = False
                            else:
                                console.print(f"  paper_count={actual} [green]OK[/green]")

                        total_themes = sum(len(p.themes) for p in resp.papers)
                        total_claims = sum(len(p.claims) for p in resp.papers)

                        if step.expect_theme_count_min is not None:
                            if total_themes < step.expect_theme_count_min:
                                console.print(
                                    f"[red]  FAIL: expected >= {step.expect_theme_count_min} "
                                    f"themes, got {total_themes}[/red]"
                                )
                                ok = False
                            else:
                                console.print(f"  themes={total_themes} [green]OK[/green]")

                        if step.expect_claim_count_min is not None:
                            if total_claims < step.expect_claim_count_min:
                                console.print(
                                    f"[red]  FAIL: expected >= {step.expect_claim_count_min} "
                                    f"claims, got {total_claims}[/red]"
                                )
                                ok = False
                            else:
                                console.print(f"  claims={total_claims} [green]OK[/green]")

                        if ok:
                            passed += 1
                        else:
                            failed += 1

                    elif step.action == "check_review":
                        if not job_id:
                            console.print("[red]  No job_id[/red]")
                            failed += 1
                            continue

                        resp = await client.get_review(job_id)
                        ok = True

                        sections = resp.review.get("sections", [])
                        if step.expect_review_sections_min is not None:
                            if len(sections) < step.expect_review_sections_min:
                                console.print(
                                    f"[red]  FAIL: expected >= {step.expect_review_sections_min} "
                                    f"sections, got {len(sections)}[/red]"
                                )
                                ok = False
                            else:
                                console.print(
                                    f"  sections={len(sections)} [green]OK[/green]"
                                )

                        if step.expect_review_has_citations:
                            import json
                            review_text = json.dumps(resp.review, default=str)
                            # Simple heuristic: citations typically contain brackets or
                            # author-year patterns
                            has_cites = "[" in review_text or "et al." in review_text
                            if not has_cites:
                                console.print("[red]  FAIL: no citations found[/red]")
                                ok = False
                            else:
                                console.print("  citations [green]OK[/green]")

                        if ok:
                            passed += 1
                        else:
                            failed += 1

                    else:
                        console.print(f"[yellow]  Unknown action: {step.action}[/yellow]")
                        failed += 1

                except PipelineError as e:
                    console.print(f"[red]  ERROR: {e}[/red]")
                    failed += 1
                except TimeoutError as e:
                    console.print(f"[red]  TIMEOUT: {e}[/red]")
                    failed += 1

        # Summary
        console.print()
        total = passed + failed
        if failed == 0:
            console.print(Panel(f"[bold green]All {total} steps passed[/bold green]"))
        else:
            console.print(Panel(
                f"[bold red]{failed}/{total} steps failed[/bold red]",
                style="red",
            ))
            raise typer.Exit(1)

    _run(_test())


@app.command(name="list-cases")
def list_cases() -> None:
    """List available test cases."""
    if not CASES_DIR.exists():
        console.print(f"[yellow]No cases directory found at {CASES_DIR}[/yellow]")
        raise typer.Exit(1)

    cases = sorted(CASES_DIR.glob("*.yaml"))
    if not cases:
        console.print("[yellow]No test cases found.[/yellow]")
        return

    from rich.table import Table

    table = Table(title="Available Test Cases")
    table.add_column("Name", style="bold")
    table.add_column("Description")

    for case_path in cases:
        with open(case_path) as f:
            raw = yaml.safe_load(f)
        tc = TestCase.model_validate(raw)
        table.add_row(case_path.stem, tc.description or tc.name)

    console.print(table)
