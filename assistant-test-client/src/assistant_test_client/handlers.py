"""Rich console handlers for streaming Socket.IO events."""

from __future__ import annotations

import time

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from assistant_test_client.schemas import (
    DoneEvent,
    ErrorEvent,
    Event,
    StepEvent,
    TokenEvent,
)

console = Console()


# ---------------------------------------------------------------------------
# TokenHandler -- streams tokens to console
# ---------------------------------------------------------------------------


class TokenHandler:
    """Accumulates tokens and renders them as Markdown in a Live display."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._buffer = ""
        self._steps: list[str] = []
        self._live: Live | None = None

    def _render(self) -> Panel:
        md = Markdown(self._buffer) if self._buffer else Text("Waiting for response...")
        return Panel(md, title="Assistant", border_style="green", expand=True)

    def start(self) -> Live:
        self._live = Live(self._render(), console=console, refresh_per_second=10)
        self._live.start()
        return self._live

    def stop(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None

    def handle(self, event: Event) -> None:
        if isinstance(event, TokenEvent):
            self._buffer += event.content
            if self._live:
                self._live.update(self._render())
        elif isinstance(event, StepEvent) and self.verbose:
            label = event.step
            console.print(f"  [dim]>> {label}[/dim]")
        elif isinstance(event, DoneEvent):
            elapsed = event.metrics.get("elapsed_time_ms", 0)
            if self._live:
                self._live.update(self._render())
            console.print(f"\n[dim]Completed in {elapsed}ms[/dim]")
        elif isinstance(event, ErrorEvent):
            console.print(f"\n[bold red]Error:[/bold red] {event.message}")


# ---------------------------------------------------------------------------
# StepHandler -- shows agent steps and tool calls
# ---------------------------------------------------------------------------


class StepHandler:
    """Prints each step event with timing."""

    def __init__(self):
        self._start = time.monotonic()

    def handle(self, event: Event) -> None:
        if isinstance(event, StepEvent):
            elapsed = int((time.monotonic() - self._start) * 1000)
            parts = [f"[cyan]{event.step}[/cyan]"]
            if event.tool:
                parts.append(f"tool=[yellow]{event.tool}[/yellow]")
            if event.agent:
                parts.append(f"agent=[magenta]{event.agent}[/magenta]")
            console.print(f"  [{elapsed}ms] " + " | ".join(parts))


# ---------------------------------------------------------------------------
# ChatHandler -- interactive chat UI
# ---------------------------------------------------------------------------


class ChatHandler:
    """Renders user and assistant messages as styled panels."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def show_user_message(self, text: str) -> None:
        panel = Panel(
            Text(text),
            title="You",
            border_style="blue",
            expand=True,
        )
        console.print(panel)

    def show_assistant_response(self, content: str, elapsed_ms: float = 0.0) -> None:
        md = Markdown(content) if content else Text("[no response]")
        panel = Panel(
            md,
            title="Assistant",
            subtitle=f"{elapsed_ms:.0f}ms" if elapsed_ms else None,
            border_style="green",
            expand=True,
        )
        console.print(panel)

    def show_error(self, message: str) -> None:
        console.print(f"[bold red]Error:[/bold red] {message}")

    def show_step(self, event: StepEvent) -> None:
        if self.verbose:
            console.print(f"  [dim]>> {event.step}[/dim]")
