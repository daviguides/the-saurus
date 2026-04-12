# Pipeline Test Client

Standalone CLI tool for testing The Saurus pipeline REST API and WebSocket streaming.

## Tech Stack

- **CLI**: Typer + Rich (progress bars, tables, Markdown rendering)
- **HTTP**: httpx (async)
- **WebSocket**: websockets
- **Schemas**: Pydantic v2
- **Test cases**: YAML

## Commands

| Command | Description |
|---------|-------------|
| `pipeline-test upload <pdfs>` | Upload PDFs, start pipeline, print job_id |
| `pipeline-test status <job_id>` | Check job status |
| `pipeline-test stream <job_id>` | Stream live WebSocket events with Rich formatting |
| `pipeline-test review <job_id>` | Fetch and render the literature review |
| `pipeline-test papers <job_id>` | Display extracted papers with themes/claims |
| `pipeline-test run <pdfs>` | Full flow: upload, stream events, show review |
| `pipeline-test test-flow <case>` | Run a YAML test case with assertions |
| `pipeline-test list-cases` | List available test cases |

## Global Options

- `--url, -u` -- Pipeline server URL (default: `http://localhost:8002`)
- `--timeout, -t` -- Timeout in seconds (default: 300)
- `--verbose, -v` -- Show all event details including agent-level events

## Development

```bash
uv sync
uv run pipeline-test --help
uv run pytest tests/ -v
```

## Test Cases

YAML files in `test-cases/cases/`. Each defines files to upload and steps with assertions (upload, wait_complete, check_status, check_papers, check_review).

Place PDF files in `test-cases/` and reference them by relative path in test cases.

## Structure

```
src/pipeline_test_client/
  cli.py        # Typer CLI commands
  client.py     # PipelineClient (async HTTP + WebSocket)
  handlers.py   # Rich console handlers (events, review, papers, progress)
  schemas.py    # Pydantic models for events, responses, test cases
```
