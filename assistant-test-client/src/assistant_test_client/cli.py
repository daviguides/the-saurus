"""Typer CLI for the assistant test client."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from assistant_test_client.client import AssistantClient
from assistant_test_client.handlers import ChatHandler, StepHandler, TokenHandler, console
from assistant_test_client.schemas import (
    DoneEvent,
    ErrorEvent,
    StepEvent,
    TestCase,
    TokenEvent,
)

app = typer.Typer(
    name="assistant-test",
    help="CLI tool for testing The Saurus conversational assistant",
    no_args_is_help=True,
)

CASES_DIR = Path(__file__).resolve().parent.parent.parent / "test-cases" / "cases"


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------

UrlOption = Annotated[
    str,
    typer.Option("--url", "-u", help="Assistant WebSocket URL"),
]
TimeoutOption = Annotated[
    float,
    typer.Option("--timeout", "-t", help="Timeout in seconds"),
]
VerboseOption = Annotated[
    bool,
    typer.Option("--verbose", "-v", help="Show step events and timing"),
]
SessionOption = Annotated[
    Optional[str],
    typer.Option("--session-id", "-s", help="Resume existing session"),
]


# ---------------------------------------------------------------------------
# connect
# ---------------------------------------------------------------------------


@app.command()
def connect(
    url: UrlOption = "http://localhost:8001",
    timeout: TimeoutOption = 60,
    verbose: VerboseOption = False,
):
    """Test Socket.IO connection and show session_id."""

    async def _run():
        client = AssistantClient(url=url, timeout=timeout)
        try:
            console.print(f"Connecting to [bold]{url}[/bold] ...")
            session_id = await client.connect()
            console.print(f"[green]Connected![/green] session_id = [bold]{session_id}[/bold]")
        except Exception as exc:
            console.print(f"[bold red]Connection failed:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc
        finally:
            await client.disconnect()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# ask
# ---------------------------------------------------------------------------


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Question to send")],
    url: UrlOption = "http://localhost:8001",
    timeout: TimeoutOption = 60,
    verbose: VerboseOption = False,
    session_id: SessionOption = None,
):
    """Send a single question and stream the response."""

    async def _run():
        client = AssistantClient(url=url, timeout=timeout)
        token_handler = TokenHandler(verbose=verbose)
        step_handler = StepHandler()

        try:
            sid = await client.connect(session_id=session_id)
            if verbose:
                console.print(f"[dim]session_id={sid}[/dim]")

            token_handler.start()
            async for event in client.send_message(question):
                token_handler.handle(event)
                if verbose:
                    step_handler.handle(event)
            token_handler.stop()

        except Exception as exc:
            token_handler.stop()
            console.print(f"[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc
        finally:
            await client.disconnect()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# chat
# ---------------------------------------------------------------------------


@app.command()
def chat(
    url: UrlOption = "http://localhost:8001",
    timeout: TimeoutOption = 60,
    verbose: VerboseOption = False,
    session_id: SessionOption = None,
):
    """Interactive chat mode with Rich formatting."""

    async def _run():
        client = AssistantClient(url=url, timeout=timeout)
        handler = ChatHandler(verbose=verbose)

        try:
            sid = await client.connect(session_id=session_id)
            console.print(f"[green]Connected![/green] session_id={sid}")
            console.print("[dim]Type your message and press Enter. Ctrl+C to exit.[/dim]\n")

            while True:
                try:
                    text = console.input("[bold blue]You:[/bold blue] ")
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[dim]Goodbye![/dim]")
                    break

                text = text.strip()
                if not text:
                    continue
                if text.lower() in ("exit", "quit", "/quit", "/exit"):
                    console.print("[dim]Goodbye![/dim]")
                    break

                handler.show_user_message(text)

                content = ""
                elapsed_ms = 0.0
                try:
                    async for event in client.send_message(text):
                        if isinstance(event, TokenEvent):
                            content += event.content
                        elif isinstance(event, StepEvent):
                            handler.show_step(event)
                        elif isinstance(event, DoneEvent):
                            elapsed_ms = event.metrics.get("elapsed_time_ms", 0)
                        elif isinstance(event, ErrorEvent):
                            handler.show_error(event.message)
                            content = ""
                            break

                    if content:
                        handler.show_assistant_response(content, elapsed_ms)
                except TimeoutError:
                    handler.show_error("Response timed out")

                console.print()

        except Exception as exc:
            console.print(f"[bold red]Connection error:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc
        finally:
            await client.disconnect()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# list-cases
# ---------------------------------------------------------------------------


@app.command("list-cases")
def list_cases():
    """List available YAML test cases."""
    if not CASES_DIR.exists():
        console.print(f"[yellow]No cases directory found at {CASES_DIR}[/yellow]")
        raise typer.Exit(code=1)

    table = Table(title="Test Cases")
    table.add_column("File", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Steps", justify="right")

    for path in sorted(CASES_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
            case = TestCase(**data)
            table.add_row(path.stem, case.name, case.description, str(len(case.steps)))
        except Exception as exc:
            table.add_row(path.stem, "[red]INVALID[/red]", str(exc), "-")

    console.print(table)


# ---------------------------------------------------------------------------
# test-flow
# ---------------------------------------------------------------------------


@app.command("test-flow")
def test_flow(
    case: Annotated[str, typer.Argument(help="Test case name (without .yaml extension)")],
    url: UrlOption = "http://localhost:8001",
    timeout: TimeoutOption = 60,
    verbose: VerboseOption = False,
):
    """Run a YAML test case with assertions."""
    case_path = CASES_DIR / f"{case}.yaml"
    if not case_path.exists():
        console.print(f"[bold red]Test case not found:[/bold red] {case_path}")
        raise typer.Exit(code=1)

    data = yaml.safe_load(case_path.read_text())
    test_case = TestCase(**data)

    async def _run():
        client = AssistantClient(url=url, timeout=test_case.timeout_seconds)
        failures: list[str] = []

        try:
            sid = await client.connect()
            console.print(f"[bold]{test_case.name}[/bold]")
            console.print(f"[dim]{test_case.description}[/dim]")
            console.print(f"[dim]session_id={sid}[/dim]\n")

            for i, step in enumerate(test_case.steps, 1):
                console.print(f"[bold cyan]Step {i}:[/bold cyan] {step.message}")

                step_timeout = step.timeout_seconds
                client._timeout = step_timeout

                try:
                    response = await client.send_and_collect(step.message)
                except RuntimeError as exc:
                    if step.expect_no_error:
                        failures.append(f"Step {i}: unexpected error: {exc}")
                        console.print(f"  [red]FAIL[/red] unexpected error: {exc}")
                    else:
                        console.print(f"  [yellow]Expected error:[/yellow] {exc}")
                    continue
                except TimeoutError:
                    failures.append(f"Step {i}: timed out after {step_timeout}s")
                    console.print(f"  [red]FAIL[/red] timed out")
                    continue

                content_lower = response.content.lower()

                # Check content contains
                for substring in step.expect_content_contains:
                    if substring.lower() not in content_lower:
                        failures.append(
                            f"Step {i}: expected response to contain '{substring}'"
                        )
                        console.print(f"  [red]FAIL[/red] missing '{substring}' in response")

                # Check content not contains
                for substring in step.expect_content_not_contains:
                    if substring.lower() in content_lower:
                        failures.append(
                            f"Step {i}: response should not contain '{substring}'"
                        )
                        console.print(f"  [red]FAIL[/red] found '{substring}' in response")

                # Check minimum steps
                if len(response.steps) < step.expect_steps_min:
                    failures.append(
                        f"Step {i}: expected >= {step.expect_steps_min} steps, got {len(response.steps)}"
                    )
                    console.print(
                        f"  [red]FAIL[/red] expected >= {step.expect_steps_min} steps, got {len(response.steps)}"
                    )

                # Check expected tools
                tools_used = {s.tool for s in response.steps if s.tool}
                for tool in step.expect_tools:
                    if tool not in tools_used:
                        failures.append(f"Step {i}: expected tool '{tool}' not called")
                        console.print(f"  [red]FAIL[/red] tool '{tool}' not called")

                if verbose:
                    console.print(f"  [dim]Response ({response.elapsed_ms:.0f}ms): {response.content[:120]}...[/dim]")

                # If no failures for this step
                step_fails = [f for f in failures if f.startswith(f"Step {i}:")]
                if not step_fails:
                    console.print(f"  [green]PASS[/green] ({response.elapsed_ms:.0f}ms)")

        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            failures.append(f"Connection error: {exc}")
        finally:
            await client.disconnect()

        # Summary
        console.print()
        if failures:
            console.print(f"[bold red]{len(failures)} failure(s):[/bold red]")
            for f in failures:
                console.print(f"  - {f}")
            raise typer.Exit(code=1)
        else:
            console.print(f"[bold green]All {len(test_case.steps)} step(s) passed![/bold green]")

    asyncio.run(_run())
