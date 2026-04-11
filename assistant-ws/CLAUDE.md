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
```
