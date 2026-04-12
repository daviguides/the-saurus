# Assistant Test Client

CLI tool for testing The Saurus conversational assistant WebSocket service.

## Setup

```bash
cd assistant-test-client
uv sync
```

## Commands

```bash
# Test connection
assistant-test connect

# Ask a single question (streams response)
assistant-test ask "What themes are in the papers?"

# Interactive chat mode
assistant-test chat

# Run a YAML test case
assistant-test test-flow basic_chat

# List available test cases
assistant-test list-cases
```

## Global Options

- `--url, -u` -- WebSocket URL (default: http://localhost:8001)
- `--timeout, -t` -- Timeout in seconds (default: 60)
- `--verbose, -v` -- Show step events and timing
- `--session-id, -s` -- Resume an existing session

## Test Cases

YAML files in `data/cases/` define automated test flows. Each case has steps with messages and assertions (content contains, tools called, minimum step events).

## Structure

```
src/assistant_test_client/
  client.py      # AsyncClient wrapper for Socket.IO /chat namespace
  schemas.py     # Pydantic models for events and test cases
  handlers.py    # Rich console output (token streaming, step display, chat UI)
  cli.py         # Typer CLI commands
```

## Tests

```bash
uv run pytest tests/
```
