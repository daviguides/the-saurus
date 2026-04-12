# Assistant WS

WebSocket backend for The Saurus assistant. Manages an Agno Team (coordinator + papers agent) and connects to `papers-mcp` for RAG.

## Tech

FastAPI, python-socketio, Agno, MCP client

## Port

8001

## Architecture

Socket.IO handles real-time chat. An Agno Team with a coordinator and a `PapersAgent` member processes queries. `PapersAgent` uses MCP tools from `papers-mcp` (port 8012) for Qdrant-backed RAG queries.

## LLM

Configurable provider. OpenAI `gpt-4o-mini` by default, Anthropic Claude as alternative.

## WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `message` | outgoing | User sends a message |
| `token` | incoming | Streamed response token |
| `done` | incoming | Response complete |
| `notification` | incoming | System notification |

## Session Management

Per-connection session with TTL.

## Config

`.env` with `AT_` prefix (pydantic-settings).

Key variables: `AT_LLM_PROVIDER`, `AT_LLM_MODEL_ID`, `AT_LLM_API_KEY`, `AT_MCP_PAPERS_URL`

## CORS

Allows `localhost:3000`, `:5173`, `:5174`.

## Structure

```
assistant_ws/
├── agents/
│   ├── coordinator/
│   │   └── team.py           # build_coordinator_team
│   └── papers/
│       └── agent.py          # build_papers_agent
└── ws/
    ├── connection.py
    ├── chat_service.py
    └── session.py
```

## Development

```bash
uv run python scripts/run_server.py    # Port 8001, hot-reload
uv run pytest tests/ -v                # Run tests
uv run ruff check .                    # Lint
```

## Integration Testing with assistant-test-client

The `assistant-test-client/` package provides a CLI for end-to-end testing against a running assistant server. Use it to validate chat interactions, tool calls, and multi-turn conversations.

### Prerequisites

The assistant depends on:
- `papers-mcp` (port 8012) for MCP tools
- `qdrant` (port 6333) for vector search
- A completed pipeline job (so there is data to query)

### Running the server in logged mode (for Claude to observe)

```bash
# From repo root:
make log-ws                          # Starts assistant-ws in background, logs to logs/assistant-ws.log
make log-mcp                         # Starts papers-mcp in background, logs to logs/papers-mcp.log
```

Claude can then read logs:
```bash
tail -f logs/assistant-ws.log        # Via Bash tool (streaming)
# or
Read logs/assistant-ws.log           # Via Read tool (snapshot)
```

### Running test cases

```bash
# From repo root:
make assistant-test ARGS="ask 'What are the main themes?'"

# Or from the test client directory:
cd assistant-test-client
uv run assistant-test connect                              # Test connection
uv run assistant-test ask "What themes were found?"        # Single question
uv run assistant-test chat                                 # Interactive mode
uv run assistant-test test-flow test-cases/cases/basic_chat.yaml    # YAML test case
uv run assistant-test list-cases                           # List available cases
```

### Test cases

Located at `assistant-test-client/test-cases/cases/`:
- `basic_chat.yaml` -- Simple question/response
- `theme_query.yaml` -- Query themes with MCP tool assertions
- `multi_turn.yaml` -- Multi-turn conversation continuity

### Workflow for Claude

1. Ensure pipeline has run (data in Qdrant): `make log-pipeline`, run a PDF, wait for completion
2. Start dependencies: `make log-mcp` then `make log-ws`
3. Run a test: `cd assistant-test-client && uv run assistant-test ask "What are the main themes?"`
4. Observe logs: `tail -100 logs/assistant-ws.log` (Agno debug mode shows Team delegation, tool calls, LLM responses)
5. For MCP tool issues: `tail -100 logs/papers-mcp.log`
6. Stop all: `make log-stop`
