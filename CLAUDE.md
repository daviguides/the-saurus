# The Saurus

Literature review pipeline — upload scientific PDFs, extract themes and claims, generate comprehensive reviews with traceable citations.

## Monorepo Structure

```
the-saurus/
├── app/                   # React 19 desktop app (upload, pipeline trace, review)
├── assistant-ui/          # Federated chat UI (Module Federation remote)
├── assistant-ws/          # Chat backend (FastAPI + Socket.IO + Agno Team)
├── papers-mcp/            # MCP server for RAG over pipeline outputs (Qdrant)
├── pipeline/              # Core pipeline engine (FastAPI + multi-agent orchestrator)
├── shared/                # Design tokens (CSS variables, light + dark themes)
├── docs/                  # Explorations and design documents
└── jobs/                  # Runtime: per-job YAML/NDJSON persistence
```

## Services

| Service | Port | Command | Description |
|---------|------|---------|-------------|
| app | 5173 | `make dev-app` | React app (Rsbuild hot-reload) |
| assistant-ui | 5174 | `make dev-ui` | Chat UI federated remote |
| assistant-ws | 8001 | `make dev-ws` | Chat WebSocket backend |
| papers-mcp | 8012 | `make dev-mcp` | MCP server for Qdrant queries |
| pipeline | 8002 | `make dev-pipeline` | Pipeline API + WebSocket events |
| qdrant | 6333 | `make dev-qdrant` | Vector database |

## Development

```bash
make setup          # Install all dependencies (uv sync + pnpm install)
make dev-pipeline   # Start pipeline backend
make dev-app        # Start React app
make dev-ui         # Start assistant-ui (federated mode: pnpm dev:federated)
make dev-ws         # Start assistant WebSocket backend
make dev-mcp        # Start papers MCP server
make dev-qdrant     # Start Qdrant in Docker
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| App | React 19 + TypeScript + Rsbuild + Tailwind v4 |
| Pipeline | Python 3.13+ + FastAPI + Agno (Gemini 2.5 Flash) |
| Assistant | Python + Agno Team + Socket.IO |
| MCP | FastMCP (Python) + Qdrant |
| Embeddings | Gemini text-embedding-004 (API) |
| Persistence | YAML + NDJSON (filesystem) |
| Design | Shared CSS tokens (light + dark), Literata + Inter + Fira Code |

## Pipeline Stages

```
Upload PDFs → Paper Analysis (themes + claims, parallel per paper)
           → Theme Dedup (semantic matching across papers)
           → Theme Review (batched, 5 themes per LLM call)
           → Aggregation (cohesive literature review with citations)
```

## Design System

Shared tokens in `shared/tokens.css`. Light theme default, dark via `class="dark"` on `<html>`.
- Primary: academic green (#2D6A4F light, #5BAB8A dark)
- Accent: gold (#D4AF37 light, #E5C349 dark)
- Headings: Literata (serif), Body: Inter (sans), Code: Fira Code (mono)

SSOT: `docs/explorations/mvp/design-system.md`

## Environment

Pipeline requires `.env` in `pipeline/` directory (see `pipeline/.env.example`):
- `PIPELINE_LLM_API_KEY` — Google AI Studio API key (Gemini)
- `PIPELINE_LLM_MAX_CONCURRENT` — concurrent LLM calls (default 2 free tier, 10 paid)

## Conventions

- Python: ruff for linting, pytest for tests, uv for package management
- TypeScript: ESLint, Rsbuild, pnpm
- Commits: conventional commits (`feat`, `fix`, `refactor`, `chore`)
- YAML for structured data, NDJSON for event streams (append-only)
- Agents use Agno framework with Pydantic structured output
- Pipeline agents satisfy `pipeline.agents.protocol.Agent` Protocol
