# The Saurus 🦕

_Feed The Saurus your papers._

A literature review pipeline that devours scientific papers and produces comprehensive, citation-backed reviews. Upload a corpus of PDFs, watch the pipeline process them in parallel, and get a structured literature review with thematic analysis and traceable citations.

## What It Does

1. **Upload** — Drop your scientific PDFs
2. **Analyze** — AI agents extract themes and claims from each paper (parallel, stateless)
3. **Deduplicate** — Semantically equivalent themes are merged across papers
4. **Review** — Deep thematic analysis synthesizes findings across papers
5. **Generate** — Cohesive literature review with inline citations `[N](p.X,§Y)`

Every claim is traceable to its source: paper, page, and paragraph.

## Prerequisites

- Python 3.13+
- Node.js 20+ with pnpm
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker (for Qdrant, optional)
- Google AI Studio API key ([get one here](https://aistudio.google.com/apikey))

## Setup

```bash
git clone https://github.com/daviguides/the-saurus.git
cd the-saurus
make setup
```

Copy environment files and set your API key:

```bash
cp pipeline/.env.example pipeline/.env
# Edit pipeline/.env and set PIPELINE_LLM_API_KEY

cp assistant-ws/.env.example assistant-ws/.env
# Edit assistant-ws/.env and set OPENAI_API_KEY (for the chat assistant)
```

## Running

### Core (pipeline + app)

The minimum to upload PDFs and generate a literature review:

```bash
# Terminal 1: Pipeline API (port 8002)
make dev-pipeline

# Terminal 2: React app (port 5173)
make dev-app
```

Open [http://localhost:5173](http://localhost:5173) and upload PDFs.

### Conversational assistant (optional)

Adds an embedded chat that can answer questions about your papers using MCP tools over Qdrant:

```bash
# Terminal 3: Qdrant vector database (port 6333)
make dev-qdrant

# Terminal 4: MCP server for RAG queries (port 8012)
make dev-mcp

# Terminal 5: Chat WebSocket backend (port 8001)
make dev-ws

# Terminal 6: Chat UI federated module (port 5174)
make dev-ui
```

### All services at once (Docker Compose)

```bash
make up      # Start all services
make down    # Stop all services
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  app (React 19)                              assistant-ui (MF)  │
│  Upload → Pipeline Trace → Review              Chat Drawer     │
├─────────────────────────────────────────────────────────────────┤
│  pipeline (FastAPI)          │  assistant-ws    │  papers-mcp    │
│  POST /jobs → run_pipeline   │  Socket.IO chat  │  Qdrant RAG    │
│  WS /jobs/{id}/stream        │  Agno Team       │  FastMCP       │
├─────────────────────────────────────────────────────────────────┤
│  Gemini 2.5 Flash (LLM)     │  Qdrant (vectors) │  YAML/NDJSON  │
└─────────────────────────────────────────────────────────────────┘
```

## Pipeline

| Stage | Agent | Parallelism | Description |
|-------|-------|-------------|-------------|
| Paper Analysis | PaperAnalyzerAgent | Per paper | Extract themes + claims in one pass |
| Theme Dedup | ThemeDedupAgent | Sequential | Merge semantic synonyms across papers |
| Theme Review | ThemeReviewerAgent | Batched (5/call) | Synthesize claims per theme |
| Aggregation | AggregatorAgent | Sequential | Cohesive review with citations |

All agents use the Agno framework with Pydantic structured output and streaming events. LLM concurrency is controlled by a shared semaphore (configurable via `PIPELINE_LLM_MAX_CONCURRENT`).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Rsbuild, Tailwind v4, Module Federation 2.0 |
| Pipeline | Python 3.13+, FastAPI, Agno, Gemini 2.5 Flash |
| Assistant | Agno Team, Socket.IO, GPT-4o-mini |
| RAG | Qdrant, Gemini text-embedding-004, FastMCP |
| Persistence | YAML (state), NDJSON (events), filesystem |
| Design | Literata + Inter + Fira Code, light/dark themes |

## Project Structure

```
the-saurus/
├── app/              # React desktop app (upload, trace, review)
├── assistant-ui/     # Federated chat UI (Module Federation remote)
├── assistant-ws/     # Chat WebSocket backend (Agno Team)
├── papers-mcp/       # MCP server (6 tools over Qdrant)
├── pipeline/         # Core pipeline engine (multi-agent orchestrator)
├── shared/           # Design tokens (CSS variables, light + dark)
├── docs/             # Architecture docs with diagrams
├── Makefile          # Dev commands
└── docker-compose.yml
```

## Configuration

| Service | Env file | Key variables |
|---------|----------|---------------|
| Pipeline | `pipeline/.env` | `PIPELINE_LLM_API_KEY`, `PIPELINE_LLM_MAX_CONCURRENT` (default 2, set 10 for paid tier) |
| Assistant | `assistant-ws/.env` | `OPENAI_API_KEY`, `AT_LLM_PROVIDER` (openai/anthropic) |
| MCP | `papers-mcp/.env` | `MCP_QDRANT_URL` (default localhost:6333) |

See each service's `.env.example` for all available settings.

## Testing

```bash
make test    # Run all test suites
make lint    # Lint all Python services

# Individual services
cd pipeline && uv run pytest tests/ -v
cd assistant-ws && uv run pytest tests/ -v
cd papers-mcp && uv run pytest tests/ -v
```

## The Name

A thesaurus connects words that mean the same thing. This pipeline does exactly that for scientific themes across papers: "chronobiology" in one paper and "circadian rhythms" in another become a single canonical theme. **The Saurus**: part thesaurus, part dinosaur.

## License

MIT
