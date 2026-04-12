"""Rich console output handlers for pipeline events and results."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from .schemas import Event, EventType, PapersResponse, ReviewResponse

console = Console()

# Map event types to display icons and colors
EVENT_STYLES: dict[str, tuple[str, str]] = {
    EventType.JOB_CREATED: ("[+]", "bold green"),
    EventType.JOB_STARTED: ("[>]", "bold blue"),
    EventType.JOB_COMPLETED: ("[ok]", "bold green"),
    EventType.JOB_FAILED: ("[!!]", "bold red"),
    EventType.STAGE_STARTED: ("[>>]", "cyan"),
    EventType.STAGE_COMPLETED: ("[<<]", "cyan"),
    EventType.STAGE_FAILED: ("[!]", "red"),
    EventType.PAPER_INGESTED: ("[P]", "yellow"),
    EventType.PAPER_PROCESSED: ("[P]", "yellow"),
    EventType.PAPER_ANALYZED: ("[P]", "green"),
    EventType.THEME_EXTRACTED: ("[T]", "magenta"),
    EventType.THEME_DEDUPLICATED: ("[T]", "magenta"),
    EventType.CLAIM_EXTRACTED: ("[C]", "blue"),
    EventType.REVIEW_GENERATED: ("[R]", "bold green"),
    EventType.AGENT_STARTED: ("[A]", "dim"),
    EventType.AGENT_TOOL_CALL: ("[A]", "dim"),
    EventType.AGENT_TOOL_RESULT: ("[A]", "dim"),
    EventType.AGENT_CONTENT: ("[A]", "dim"),
    EventType.AGENT_COMPLETED: ("[A]", "dim"),
    EventType.AGENT_ERROR: ("[A!]", "red"),
}

# Pipeline stages in order for progress tracking
PIPELINE_STAGES = [
    "paper_analysis",
    "theme_dedup",
    "theme_review",
    "aggregation",
]


class EventHandler:
    """Displays pipeline events in the console with styling."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._start_time: datetime | None = None

    async def handle(self, event: Event) -> None:
        """Process and display a single event."""
        if self._start_time is None:
            self._start_time = datetime.now(timezone.utc)

        icon, style = EVENT_STYLES.get(event.event_type, ("[-]", "white"))

        # Skip agent-level detail unless verbose
        if not self.verbose and event.event_type in (
            EventType.AGENT_STARTED,
            EventType.AGENT_TOOL_CALL,
            EventType.AGENT_TOOL_RESULT,
            EventType.AGENT_CONTENT,
            EventType.AGENT_COMPLETED,
        ):
            return

        # Build display line
        ts = event.timestamp.strftime("%H:%M:%S")
        msg = self._format_payload(event)

        text = Text()
        text.append(f"{ts} ", style="dim")
        text.append(f"{icon} ", style=style)
        text.append(event.event_type, style=style)
        if msg:
            text.append(f"  {msg}")

        console.print(text)

    def _format_payload(self, event: Event) -> str:
        """Extract a human-readable summary from the event payload."""
        p = event.payload
        parts: list[str] = []

        if event.event_type == EventType.JOB_CREATED:
            count = p.get("paper_count", "?")
            filenames = p.get("filenames", [])
            parts.append(f"{count} paper(s): {', '.join(filenames)}")

        elif event.event_type == EventType.STAGE_STARTED:
            parts.append(p.get("stage", ""))

        elif event.event_type == EventType.STAGE_COMPLETED:
            stage = p.get("stage", "")
            elapsed = p.get("elapsed_seconds", "")
            parts.append(f"{stage}")
            if elapsed:
                parts.append(f"({elapsed:.1f}s)")

        elif event.event_type == EventType.PAPER_ANALYZED:
            title = p.get("title", p.get("paper_id", ""))
            themes = p.get("theme_count", "?")
            claims = p.get("claim_count", "?")
            parts.append(f"{title} -- {themes} themes, {claims} claims")

        elif event.event_type == EventType.THEME_DEDUPLICATED:
            original = p.get("original_count", "?")
            deduped = p.get("deduplicated_count", "?")
            parts.append(f"{original} -> {deduped} themes")

        elif event.event_type == EventType.JOB_FAILED:
            parts.append(p.get("error", "unknown error"))

        elif self.verbose:
            # Show full payload in verbose mode for any event
            if p:
                import json

                parts.append(json.dumps(p, default=str)[:200])

        return " ".join(parts)


class ReviewHandler:
    """Renders the literature review using Rich Markdown."""

    @staticmethod
    def display(review_data: dict) -> None:
        """Display the review as formatted Markdown in the console."""
        # The review.yaml structure varies, but typically has markdown content
        sections = review_data.get("sections", [])
        title = review_data.get("title", "Literature Review")

        console.print()
        console.print(Panel(f"[bold]{title}[/bold]", style="green"))
        console.print()

        if isinstance(sections, list):
            for section in sections:
                if isinstance(section, dict):
                    heading = section.get("heading", "")
                    body = section.get("body", section.get("content", ""))
                    if heading:
                        console.print(Markdown(f"## {heading}"))
                    if body:
                        console.print(Markdown(body))
                    console.print()
                elif isinstance(section, str):
                    console.print(Markdown(section))
                    console.print()
        elif isinstance(review_data.get("content"), str):
            console.print(Markdown(review_data["content"]))
        else:
            # Fallback: dump the review as-is
            import json

            console.print(Markdown(f"```json\n{json.dumps(review_data, indent=2, default=str)}\n```"))


class PapersHandler:
    """Displays extracted papers with their themes and claims."""

    @staticmethod
    def display(papers_resp: PapersResponse) -> None:
        """Display papers in a table with theme/claim counts."""
        table = Table(title="Extracted Papers", show_lines=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="bold", max_width=50)
        table.add_column("Authors", max_width=30)
        table.add_column("Pages", justify="right")
        table.add_column("Themes", justify="right", style="magenta")
        table.add_column("Claims", justify="right", style="blue")

        for i, paper in enumerate(papers_resp.papers, 1):
            authors = ", ".join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors += " et al."
            table.add_row(
                str(i),
                paper.title or paper.filename,
                authors,
                str(paper.page_count),
                str(len(paper.themes)),
                str(len(paper.claims)),
            )

        console.print()
        console.print(table)

        # Show theme details
        for paper in papers_resp.papers:
            if paper.themes:
                console.print()
                console.print(
                    Panel(
                        f"[bold]{paper.title or paper.filename}[/bold] -- Themes",
                        style="magenta",
                    )
                )
                for theme in paper.themes:
                    name = theme.get("name", theme.get("theme", "?"))
                    desc = theme.get("description", "")
                    console.print(f"  [magenta]* {name}[/magenta]")
                    if desc:
                        console.print(f"    {desc}")


class ProgressHandler:
    """Shows a progress bar for pipeline stages."""

    def __init__(self) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        )
        self._tasks: dict[str, int] = {}
        self._stage_index = 0

    def __enter__(self) -> ProgressHandler:
        self._progress.__enter__()
        total = len(PIPELINE_STAGES)
        self._main_task = self._progress.add_task("Pipeline", total=total)
        return self

    def __exit__(self, *exc: object) -> None:
        self._progress.__exit__(*exc)

    async def handle(self, event: Event) -> None:
        """Update progress based on pipeline events."""
        if event.event_type == EventType.STAGE_STARTED:
            stage = event.payload.get("stage", "")
            if stage in PIPELINE_STAGES:
                idx = PIPELINE_STAGES.index(stage)
                self._progress.update(self._main_task, completed=idx)
                self._progress.update(
                    self._main_task,
                    description=f"Pipeline: {stage.replace('_', ' ').title()}",
                )

        elif event.event_type == EventType.STAGE_COMPLETED:
            stage = event.payload.get("stage", "")
            if stage in PIPELINE_STAGES:
                idx = PIPELINE_STAGES.index(stage) + 1
                self._progress.update(self._main_task, completed=idx)

        elif event.event_type in (EventType.JOB_COMPLETED, EventType.JOB_FAILED):
            self._progress.update(
                self._main_task,
                completed=len(PIPELINE_STAGES),
                description=f"Pipeline: {event.event_type.replace('job_', '').title()}",
            )
