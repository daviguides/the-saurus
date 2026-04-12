# The Saurus

Literature review pipeline — upload scientific PDFs, extract themes and claims, generate comprehensive reviews with traceable citations, and chat with your papers through an embedded conversational assistant.

## Monorepo Structure

```
the-saurus/
├── app/                    # React 19 desktop app (upload, pipeline trace, review)
├── assistant-ui/           # Federated chat UI (Module Federation remote)
├── assistant-ws/           # Chat backend (FastAPI + Socket.IO + Agno Team)
├── papers-mcp/             # MCP server for RAG over pipeline outputs (Qdrant)
├── pipeline/               # Core pipeline engine (FastAPI + Restate + multi-agent orchestrator)
├── evals/                  # Evaluation suite (RAGAS + DeepEval + Langfuse)
├── infra/
│   ├── terraform/          # AWS infrastructure (EKS, Aurora, ElastiCache, S3)
│   └── helm/the-saurus/    # Kubernetes deployment (all services + Langfuse + Restate)
├── pipeline-test-client/   # CLI for end-to-end pipeline testing
├── assistant-test-client/  # CLI for end-to-end assistant testing
├── shared/                 # Design tokens (CSS variables, light + dark themes)
├── docs/                   # Architecture docs, diagrams, design foundation
├── .github/workflows/      # CI (lint + test) + eval regression
└── jobs/                   # Runtime: per-job YAML/NDJSON persistence
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
| restate | 8080 | `make dev-restate` | Durable execution server |
| langfuse | 3000 | `make eval-langfuse` | LLM observability |

## Development

```bash
make setup          # Install all dependencies (uv sync + pnpm install)
make dev-pipeline   # Start pipeline backend
make dev-app        # Start React app
make dev-restate    # Start Restate durable execution server (Docker)
make register-restate  # Register pipeline workflow (one-time)
make dev-ui         # Start assistant-ui (federated mode)
make dev-ws         # Start assistant WebSocket backend
make dev-mcp        # Start papers MCP server
make dev-qdrant     # Start Qdrant in Docker
make test           # Run all test suites
make lint           # Lint all Python services
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| App | React 19 + TypeScript + Rsbuild + Tailwind v4 + Module Federation 2.0 |
| Pipeline | Python 3.13+ + FastAPI + Restate + Agno (Gemini 2.5 Flash) |
| Assistant | Python + Agno Team + Socket.IO + GPT-4o-mini |
| MCP | FastMCP (Python) + Qdrant |
| Embeddings | Gemini text-embedding-004 (API) |
| Observability | Langfuse + ClickHouse + OpenLIT |
| Infrastructure | Terraform (AWS) + Helm (Kubernetes) + Docker Compose |
| Persistence | YAML + NDJSON (filesystem, fsync per event) |
| Design | Shared CSS tokens (light + dark), Literata + Inter + Fira Code |

## Pipeline Stages

```
Upload PDFs → Paper Analysis (themes + claims, parallel per paper)
           → Theme Dedup (semantic matching across papers)
           → Theme Review (batched, 5 themes per LLM call, parallel batches)
           → Aggregation (cohesive literature review with citations)
```

Each stage is a durable step orchestrated via Restate workflow. On crash, completed stages are replayed from journal without re-execution. Falls back to in-process asyncio if Restate is unavailable.

## Agent Architecture

- All agents use Agno with `output_schema` + `structured_outputs=True`
- Streaming events via `arun(stream=True, stream_events=True)`
- Event bridge maps 6 Agno lifecycle events to pipeline EventTypes
- `run_agent_with_retry` provides semaphore concurrency, exponential backoff, timeout
- Agents satisfy `pipeline.agents.protocol.Agent` Protocol (runtime-checkable)
- Stub agents in `pipeline.agents.stubs` for testing

## Error Handling

Custom exception hierarchy in `pipeline/core/exceptions.py`:
- `PipelineError` (base)
  - `StageError(stage)` — failure in a pipeline stage
  - `AgentError(agent_name)` — LLM agent failure
    - `AgentResponseError` — invalid/empty LLM response
  - `PersistenceError` — YAML read/write failure
  - `IngestionError` — PDF extraction failure

Partial failure tolerated: pipeline continues if some papers fail analysis.

## Security

- Opt-in API key auth (`PIPELINE_API_KEY`): enforced only when set
- Path traversal protection on job IDs and filenames
- PDF magic bytes validation + 50MB size limit + 50 file count limit
- Error messages sanitized (no internal details to clients)
- `yaml.safe_load` / `yaml.safe_dump` only

## Design System

Shared tokens in `shared/tokens.css`. Light theme default, dark via `class="dark"` on `<html>`.
- Primary: academic green (#2D6A4F light, #5BAB8A dark)
- Accent: gold (#D4AF37 light, #E5C349 dark)
- Theme chip colors as CSS variables with dark mode overrides
- Headings: Literata (serif), Body: Inter (sans), Code: Fira Code (mono)
- Print CSS for review export
- `prefers-reduced-motion` support

SSOT: `docs/foundation/design-system.md`

## Environment

Pipeline requires `.env` in `pipeline/` directory (see `pipeline/.env.example`):
- `PIPELINE_LLM_API_KEY` — Google AI Studio API key (Gemini)
- `PIPELINE_LLM_MAX_CONCURRENT` — concurrent LLM calls (default 2 free tier, 10 paid)
- `PIPELINE_API_KEY` — optional, enables auth when set
- `PIPELINE_RESTATE_INGRESS_URL` — Restate server (default http://localhost:8080)

## Testing

| Suite | Tests | Includes |
|-------|-------|----------|
| Pipeline | 266 | Agents, orchestrator, events, persistence, API, WebSocket, security, property-based (Hypothesis) |
| Assistant WS | 70 | ChatService, sessions, schemas, connections |
| Test clients | 34 | End-to-end pipeline + assistant CLI tools |

Test markers: `unit`, `integration`, `property`, `slow`

## Conventions

- Python: ruff for linting, pytest for tests, uv for package management
- TypeScript: ESLint, Rsbuild, pnpm
- Commits: conventional commits (`feat`, `fix`, `refactor`, `chore`, `test`, `ci`, `docs`, `perf`)
- YAML for structured data, NDJSON for event streams (append-only, fsync)
- Agents use Agno framework with Pydantic structured output
- Infrastructure as code: Terraform (AWS) + Helm (Kubernetes)
